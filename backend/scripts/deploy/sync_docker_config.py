#!/usr/bin/env python3
"""
Docker Configuration Sync Script for TovPlay
Synchronizes local Docker configurations with server deployment
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional

class DockerConfigSync:
    def __init__(self, environment: str = 'production'):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent.parent
        self.compose_file = f'docker-compose.{environment}.yml'
        
    def check_current_containers(self, ssh_command: str) -> Dict:
        """Check currently running containers on server."""
        cmd = f'{ssh_command} "docker ps -a --format json"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to get container info: {result.stderr}")
                return {}
            
            containers = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container = json.loads(line)
                        containers[container['Names']] = container
                    except json.JSONDecodeError:
                        continue
            
            return containers
            
        except Exception as e:
            print(f"❌ Error checking containers: {e}")
            return {}
    
    def backup_current_deployment(self, ssh_command: str) -> bool:
        """Backup current deployment configuration."""
        backup_commands = [
            "mkdir -p /var/www/backup/$(date +%Y%m%d_%H%M%S)",
            f"BACKUP_DIR=/var/www/backup/$(date +%Y%m%d_%H%M%S)",
            
            # Backup container configurations
            "docker inspect backend > $BACKUP_DIR/backend_config.json 2>/dev/null || true",
            "docker inspect tovplay-frontend > $BACKUP_DIR/frontend_config.json 2>/dev/null || true",
            
            # Backup environment if exists
            "cp /var/www/tovplay/.env* $BACKUP_DIR/ 2>/dev/null || true",
            
            # Save current running command
            "docker ps --format 'table {{.Names}}\\t{{.Command}}\\t{{.Ports}}' > $BACKUP_DIR/running_containers.txt",
            
            "echo 'Backup created in:' && echo $BACKUP_DIR"
        ]
        
        cmd = f'{ssh_command} "{"; ".join(backup_commands)}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Current deployment backed up successfully")
                print(f"Backup location: {result.stdout.strip().split()[-1]}")
                return True
            else:
                print(f"⚠️  Backup creation had issues: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    def stop_current_containers(self, ssh_command: str) -> bool:
        """Stop current containers gracefully."""
        stop_commands = [
            # Stop containers gracefully
            "docker stop backend 2>/dev/null || true",
            "docker stop tovplay-frontend 2>/dev/null || true",
            
            # Wait a moment
            "sleep 5",
            
            # Remove containers
            "docker rm backend 2>/dev/null || true",
            "docker rm tovplay-frontend 2>/dev/null || true",
            
            # Clean up unused networks
            "docker network prune -f",
            
            "echo 'Containers stopped and removed'"
        ]
        
        cmd = f'{ssh_command} "{"; ".join(stop_commands)}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Current containers stopped successfully")
                return True
            else:
                print(f"⚠️  Some containers may not have stopped cleanly: {result.stderr}")
                return True  # Continue anyway
        except Exception as e:
            print(f"❌ Error stopping containers: {e}")
            return False
    
    def deploy_docker_compose(self, ssh_command: str) -> bool:
        """Deploy new Docker Compose configuration."""
        # First, upload the compose file
        compose_file_path = self.project_root / self.compose_file
        
        if not compose_file_path.exists():
            print(f"❌ Compose file not found: {compose_file_path}")
            return False
        
        # Create deployment directory structure
        setup_commands = [
            "mkdir -p /var/www/tovplay/docker",
            f"cd /var/www/tovplay/docker"
        ]
        
        # Upload docker-compose file
        upload_cmd = f'scp -o StrictHostKeyChecking=no {compose_file_path} admin@193.181.213.220:/var/www/tovplay/docker/'
        
        try:
            result = subprocess.run(upload_cmd, shell=True)
            if result.returncode != 0:
                print(f"❌ Failed to upload compose file")
                return False
            
            print(f"✅ Uploaded {self.compose_file}")
        except Exception as e:
            print(f"❌ Error uploading compose file: {e}")
            return False
        
        # Deploy with Docker Compose
        deploy_commands = [
            "cd /var/www/tovplay/docker",
            f"cp {self.compose_file} docker-compose.yml",
            
            # Load environment variables from parent directory
            "cp ../.env .env 2>/dev/null || true",
            
            # Pull latest images
            "docker-compose pull",
            
            # Start services
            "docker-compose up -d",
            
            # Show status
            "docker-compose ps",
            "docker-compose logs --tail=50 backend"
        ]
        
        cmd = f'{ssh_command} "{"; ".join(deploy_commands)}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker Compose deployment successful")
                print("📊 Container status:")
                print(result.stdout)
                return True
            else:
                print(f"❌ Docker Compose deployment failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error deploying Docker Compose: {e}")
            return False
    
    def verify_deployment(self, ssh_command: str) -> bool:
        """Verify that the deployment is working correctly."""
        verify_commands = [
            "cd /var/www/tovplay/docker",
            
            # Check container health
            "echo '=== Container Status ==='",
            "docker-compose ps",
            
            # Check health endpoints
            "echo '=== Health Check ==='",
            "curl -f http://localhost:8000/health -m 10 || echo 'Health check failed'",
            
            # Check logs for errors
            "echo '=== Recent Logs (last 20 lines) ==='", 
            "docker-compose logs --tail=20 backend",
            
            # Check if service is responding
            "echo '=== Service Response ==='",
            "curl -s http://localhost:8000/api/ -m 10 || echo 'API not responding'"
        ]
        
        cmd = f'{ssh_command} "{"; ".join(verify_commands)}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print("📋 Deployment Verification Results:")
            print(result.stdout)
            
            # Check if health endpoint responded
            if "healthy" in result.stdout.lower() and "HTTP" not in result.stderr:
                print("✅ Deployment verification passed")
                return True
            else:
                print("⚠️  Deployment verification had issues - manual check recommended")
                return False
                
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            return False
    
    def rollback_deployment(self, ssh_command: str, backup_dir: str) -> bool:
        """Rollback to previous deployment if needed."""
        rollback_commands = [
            f"cd {backup_dir}",
            
            # Stop current containers
            "docker stop backend tovplay-frontend 2>/dev/null || true",
            "docker rm backend tovplay-frontend 2>/dev/null || true",
            
            # Restore from backup (simplified - restart with previous image)
            "cd /var/www/tovplay/docker",
            "docker-compose down",
            
            # Restart with rollback configuration
            "docker run -d --name backend --restart unless-stopped -p 8000:5001 "
            "-e FLASK_ENV=production "
            "-e DATABASE_URL='postgresql://raz%40tovtech.org:CaptainForgotCreatureBreak@localhost:5432/tovplay' "
            "tovtech/tovplaybackend:latest "
            "gunicorn -w 4 -b 0.0.0.0:5001 --chdir /app/src app:create_app()",
            
            "echo 'Rollback completed'"
        ]
        
        cmd = f'{ssh_command} "{"; ".join(rollback_commands)}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Rollback completed successfully")
                return True
            else:
                print(f"❌ Rollback failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error during rollback: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Sync Docker configuration with TovPlay server')
    parser.add_argument(
        '--environment', '-e',
        choices=['staging', 'production'],
        default='production',
        help='Target environment (default: production)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    parser.add_argument(
        '--backup-only',
        action='store_true',
        help='Only create backup, do not deploy'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify current deployment'
    )
    parser.add_argument(
        '--rollback',
        help='Rollback to specified backup directory'
    )
    
    args = parser.parse_args()
    
    # SSH command setup
    ssh_command = 'wsl -e sshpass -p "EbTyNkfJG6LM" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@193.181.213.220 "sudo -s"'
    
    syncer = DockerConfigSync(args.environment)
    
    print(f"🚀 Docker Configuration Sync - {args.environment.upper()} Environment")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print(f"Would sync: {syncer.compose_file}")
        return 0
    
    if args.rollback:
        print(f"🔄 Rolling back to: {args.rollback}")
        success = syncer.rollback_deployment(ssh_command, args.rollback)
        return 0 if success else 1
    
    if args.verify_only:
        print("🔍 Verifying current deployment...")
        success = syncer.verify_deployment(ssh_command)
        return 0 if success else 1
    
    # Full deployment process
    success = True
    
    # Step 1: Check current state
    print("📊 Checking current containers...")
    containers = syncer.check_current_containers(ssh_command)
    for name, info in containers.items():
        print(f"   {name}: {info.get('State', 'unknown')} - {info.get('Status', 'unknown')}")
    
    # Step 2: Backup current deployment
    print("\n💾 Creating backup...")
    backup_success = syncer.backup_current_deployment(ssh_command)
    
    if not backup_success:
        print("⚠️  Backup failed - continuing anyway (risky)")
    
    if args.backup_only:
        print("✅ Backup completed")
        return 0
    
    # Step 3: Stop current containers
    print("\n🛑 Stopping current containers...")
    stop_success = syncer.stop_current_containers(ssh_command)
    
    if not stop_success:
        print("❌ Failed to stop containers - aborting")
        return 1
    
    # Step 4: Deploy new configuration  
    print(f"\n🚀 Deploying {syncer.compose_file}...")
    deploy_success = syncer.deploy_docker_compose(ssh_command)
    
    if not deploy_success:
        print("❌ Deployment failed")
        success = False
    
    # Step 5: Verify deployment
    print("\n🔍 Verifying deployment...")
    verify_success = syncer.verify_deployment(ssh_command)
    
    if not verify_success:
        print("⚠️  Verification failed - manual check recommended")
        success = False
    
    # Final status
    if success:
        print("\n✅ Docker configuration sync completed successfully!")
        print("🌐 Service should be available at: http://193.181.213.220:8000")
    else:
        print("\n❌ Docker configuration sync had issues")
        print("💡 Check logs and consider rollback if necessary")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())