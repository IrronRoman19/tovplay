"""
TovPlay Secure Configuration Management
Handles environment-specific configuration loading with validation and security checks
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from urllib.parse import urlparse

# Configuration validation patterns
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'


@dataclass
class DatabaseConfig:
    """Database configuration with validation."""
    user: str
    password: str
    host: str
    port: int
    database: str
    url: str
    
    def __post_init__(self):
        """Validate database configuration."""
        if not all([self.user, self.password, self.host, self.database]):
            raise ValueError("Missing required database configuration")
        
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid database port: {self.port}")
        
        # Validate URL format
        try:
            parsed = urlparse(self.url)
            if not parsed.scheme or not parsed.hostname:
                raise ValueError("Invalid database URL format")
        except Exception as e:
            raise ValueError(f"Invalid database URL: {e}")


@dataclass
class EmailConfig:
    """Email configuration with validation."""
    sender: str
    password: str
    smtp_server: str
    smtp_port: int = 465
    
    def __post_init__(self):
        """Validate email configuration."""
        if not self.sender or '@' not in self.sender:
            raise ValueError("Invalid email sender address")
        
        if not self.password or len(self.password) < 8:
            raise ValueError("Email password too weak (minimum 8 characters)")
        
        if not self.smtp_server:
            raise ValueError("SMTP server is required")


@dataclass
class SecurityConfig:
    """Security configuration with validation."""
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    allowed_origins: list = field(default_factory=list)
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 3600
    
    def __post_init__(self):
        """Validate security configuration."""
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError("Flask SECRET_KEY too weak (minimum 32 characters)")
        
        if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
            raise ValueError("JWT secret key too weak (minimum 32 characters)")
        
        if self.secret_key == self.jwt_secret_key:
            warnings.warn("Flask SECRET_KEY and JWT_SECRET_KEY should be different")
        
        # Check for weak/default keys
        weak_keys = [
            'your-secret-key-here',
            'your-super-secret-key-that-is-not-in-your-code',
            'development-key',
            'secret',
            'password'
        ]
        
        for key in [self.secret_key, self.jwt_secret_key]:
            if any(weak in key.lower() for weak in weak_keys):
                raise ValueError("Using weak or default secret key")


@dataclass 
class AppConfig:
    """Application configuration with validation."""
    flask_app: str
    flask_env: str
    debug: bool = False
    testing: bool = False
    log_level: str = "INFO"
    log_format: str = "json"
    
    def __post_init__(self):
        """Validate application configuration."""
        valid_envs = ['development', 'testing', 'staging', 'production']
        if self.flask_env not in valid_envs:
            raise ValueError(f"Invalid FLASK_ENV: {self.flask_env}. Must be one of {valid_envs}")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"Invalid LOG_LEVEL: {self.log_level}")
        
        # Security checks based on environment
        if self.flask_env == 'production':
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")
            if self.testing:
                raise ValueError("Testing mode must be disabled in production")


class SecureConfigLoader:
    """Secure configuration loader with environment-specific validation."""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment: str = environment or os.getenv('FLASK_ENV', 'development') or 'development'
        self.project_root = Path(__file__).parent.parent.parent
        self._config_cache: Dict[str, Any] = {}
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_env_file(self, env_file: Optional[Union[str, Path]] = None) -> Dict[str, str]:
        """Load environment variables from file with security validation."""
        if env_file is None:
            env_file = self.project_root / f'.env.{self.environment}'
        
        env_file = Path(env_file)
        env_vars: Dict[str, str] = {}
        
        if not env_file.exists():
            self.logger.warning(f"Environment file not found: {env_file}")
            return env_vars
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        self.logger.warning(f"Invalid line {line_num} in {env_file}: {line}")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Security check: don't load variables with placeholder values
                    if self._is_placeholder_value(value):
                        self.logger.warning(f"Placeholder value detected for {key}, skipping")
                        continue
                    
                    env_vars[key] = value
                    
                    # Set environment variable if not already set
                    if key not in os.environ:
                        os.environ[key] = value
        
        except Exception as e:
            self.logger.error(f"Error loading environment file {env_file}: {e}")
            raise
        
        return env_vars
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if value is a placeholder that should not be used."""
        placeholders = [
            'your-',
            'replace-',
            'change-',
            'example-',
            'template-',
            'placeholder',
            '${',
            'TODO:',
            'FIXME:'
        ]
        
        return any(placeholder in value.lower() for placeholder in placeholders)
    
    def get_database_config(self) -> DatabaseConfig:
        """Get validated database configuration with UTF-8 support."""
        cache_key = 'database_config'
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            # Get the base database URL
            db_url = os.environ['DATABASE_URL']
            
            # Ensure the URL includes UTF-8 encoding parameters
            if 'postgresql' in db_url and '?charset=' not in db_url:
                if '?' in db_url:
                    db_url += '&client_encoding=utf8'
                else:
                    db_url += '?client_encoding=utf8'
            elif 'mysql' in db_url and '?charset=' not in db_url:
                if '?' in db_url:
                    db_url += '&charset=utf8mb4'
                else:
                    db_url += '?charset=utf8mb4'
            
            config = DatabaseConfig(
                user=os.environ['POSTGRES_USER'],
                password=os.environ['POSTGRES_PASSWORD'],
                host=os.environ['POSTGRES_HOST'],
                port=int(os.environ['POSTGRES_PORT']),
                database=os.environ['POSTGRES_DB'],
                url=db_url  # Use the updated URL with encoding parameters
            )
            
            self._config_cache[cache_key] = config
            return config
            
        except Exception as e:
            self.logger.error(f"Invalid database configuration: {e}")
            raise
    
    def get_email_config(self) -> EmailConfig:
        """Get validated email configuration."""
        cache_key = 'email_config'
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            config = EmailConfig(
                sender=self._get_required_env('EMAIL_SENDER'),
                password=self._get_required_env('EMAIL_PASSWORD'),
                smtp_server=self._get_required_env('SMTP_SERVER'),
                smtp_port=int(self._get_required_env('SMTP_PORT', '465'))
            )
            
            self._config_cache[cache_key] = config
            return config
            
        except Exception as e:
            self.logger.error(f"Invalid email configuration: {e}")
            raise
    
    def get_security_config(self) -> SecurityConfig:
        """Get validated security configuration."""
        cache_key = 'security_config'
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            allowed_origins_str = self._get_required_env('ALLOWED_ORIGINS', '')
            allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',') if origin.strip()]
            
            config = SecurityConfig(
                secret_key=self._get_required_env('SECRET_KEY'),
                jwt_secret_key=self._get_required_env('JWT_SECRET_KEY'),
                jwt_algorithm=self._get_required_env('JWT_ALGORITHM', 'HS256'),
                allowed_origins=allowed_origins,
                rate_limit_per_minute=int(self._get_required_env('RATE_LIMIT_PER_MINUTE', '60')),
                rate_limit_per_hour=int(self._get_required_env('RATE_LIMIT_PER_HOUR', '3600'))
            )
            
            self._config_cache[cache_key] = config
            return config
            
        except Exception as e:
            self.logger.error(f"Invalid security configuration: {e}")
            raise
    
    def get_app_config(self) -> AppConfig:
        """Get validated application configuration."""
        cache_key = 'app_config'
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            config = AppConfig(
                flask_app=self._get_required_env('FLASK_APP'),
                flask_env=self.environment,
                debug=self.environment == 'development',
                testing=self.environment == 'testing',
                log_level=self._get_required_env('LOG_LEVEL', 'INFO'),
                log_format=self._get_required_env('LOG_FORMAT', 'json')
            )
            
            self._config_cache[cache_key] = config
            return config
            
        except Exception as e:
            self.logger.error(f"Invalid application configuration: {e}")
            raise
    
    def _get_required_env(self, key: str, default: Optional[str] = None) -> str:
        """Get required environment variable with optional default."""
        value = os.getenv(key, default)
        
        if value is None:
            raise ValueError(f"Required environment variable not set: {key}")
        
        if self._is_placeholder_value(value):
            raise ValueError(f"Placeholder value detected for required variable: {key}")
        
        return value
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate complete configuration and return status."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'environment': self.environment
        }
        
        try:
            # Validate each configuration section
            configs = [
                ('database', self.get_database_config),
                ('email', self.get_email_config), 
                ('security', self.get_security_config),
                ('app', self.get_app_config)
            ]
            
            for name, config_func in configs:
                try:
                    config_func()
                    self.logger.info(f"✅ {name.title()} configuration validated successfully")
                except Exception as e:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"{name}: {str(e)}")
                    self.logger.error(f"❌ {name.title()} configuration validation failed: {e}")
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Configuration validation error: {str(e)}")
        
        # Environment-specific warnings
        if self.environment == 'production':
            if os.getenv('DEBUG', '').lower() in ('true', '1', 'yes'):
                validation_result['warnings'].append("Debug mode should be disabled in production")
        
        return validation_result
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-compatible configuration dictionary."""
        db_config = self.get_database_config()
        email_config = self.get_email_config()
        security_config = self.get_security_config()
        app_config = self.get_app_config()
        
        return {
            # Flask core
            'SECRET_KEY': security_config.secret_key,
            'DEBUG': app_config.debug,
            'TESTING': app_config.testing,
            'ENV': app_config.flask_env,
            
            # Database with connection pooling to prevent max_connections exhaustion
            'SQLALCHEMY_DATABASE_URI': db_config.url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': 5,              # Max persistent connections (reduced from 10)
                'max_overflow': 5,           # Max temporary connections beyond pool_size
                'pool_timeout': 30,          # Seconds to wait for connection
                'pool_recycle': 300,         # Recycle connections after 5 minutes
                'pool_pre_ping': True,       # Verify connection before use
                'connect_args': {
                    'connect_timeout': 10,   # Connection timeout
                    'options': '-c statement_timeout=30000'  # Statement timeout 30s
                }
            },
            
            # JWT
            'JWT_SECRET_KEY': security_config.jwt_secret_key,
            'JWT_ALGORITHM': security_config.jwt_algorithm,
            'JWT_ACCESS_TOKEN_EXPIRES': 86400,  # 24 hours
            
            # Email
            'MAIL_SERVER': email_config.smtp_server,
            'MAIL_PORT': email_config.smtp_port,
            'MAIL_USE_SSL': True,
            'MAIL_USERNAME': email_config.sender,
            'MAIL_PASSWORD': email_config.password,
            'MAIL_DEFAULT_SENDER': email_config.sender,
            
            # Security
            'CORS_ORIGINS': security_config.allowed_origins,
            'RATE_LIMIT_PER_MINUTE': security_config.rate_limit_per_minute,
            'RATE_LIMIT_PER_HOUR': security_config.rate_limit_per_hour,
            
            # Logging
            'LOG_LEVEL': app_config.log_level,
            'LOG_FORMAT': app_config.log_format,
        }


# Global instance
_config_loader: Optional[SecureConfigLoader] = None


def get_config_loader(environment: Optional[str] = None) -> SecureConfigLoader:
    """Get or create global configuration loader instance."""
    global _config_loader
    
    if _config_loader is None or (environment and _config_loader.environment != environment):
        _config_loader = SecureConfigLoader(environment)
        _config_loader.load_env_file()  # Load environment variables
    
    return _config_loader


def get_flask_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """Get Flask configuration dictionary."""
    loader = get_config_loader(environment)
    return loader.get_flask_config()


def validate_environment(environment: Optional[str] = None) -> Dict[str, Any]:
    """Validate environment configuration."""
    loader = get_config_loader(environment)
    return loader.validate_configuration()