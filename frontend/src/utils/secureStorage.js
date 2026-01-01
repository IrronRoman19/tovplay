import CryptoJS from 'crypto-js';

/**
 * Secure Storage Utility
 * Provides encrypted storage for sensitive data using AES encryption
 */
class SecureStorage {
  constructor() {
    // Generate encryption key from device-specific data
    this.encryptionKey = this.generateEncryptionKey();
    this.sessionKey = this.generateSessionKey();
  }

  /**
   * Generate device-specific encryption key
   */
  generateEncryptionKey() {
    const deviceFingerprint = this.getDeviceFingerprint();
    const baseKey = 'TovPlay_Secure_Key_' + deviceFingerprint;
    return CryptoJS.SHA256(baseKey).toString();
  }

  /**
   * Generate session-specific key for additional security
   */
  generateSessionKey() {
    const sessionData = Date.now() + Math.random();
    return CryptoJS.SHA256(sessionData.toString()).toString().substr(0, 32);
  }

  /**
   * Get device fingerprint
   */
  getDeviceFingerprint() {
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillText('Fingerprint', 2, 2);
      const fingerprint = canvas.toDataURL().slice(-50);
      return fingerprint;
    } catch {
      return 'default_fingerprint';
    }
  }

  /**
   * Encrypt data before storage
   */
  encrypt(data) {
    try {
      const encrypted = CryptoJS.AES.encrypt(JSON.stringify(data), this.encryptionKey).toString();
      return btoa(encrypted); // Base64 encode for safe storage
    } catch (error) {
      console.error('Encryption failed:', error);
      return null;
    }
  }

  /**
   * Decrypt data from storage
   */
  decrypt(encryptedData) {
    try {
      const decoded = atob(encryptedData); // Base64 decode
      const decrypted = CryptoJS.AES.decrypt(decoded, this.encryptionKey);
      const decryptedString = decrypted.toString(CryptoJS.enc.Utf8);
      return JSON.parse(decryptedString);
    } catch (error) {
      console.error('Decryption failed:', error);
      return null;
    }
  }

  /**
   * Secure set operation with TTL support
   */
  set(key, value, ttlMs = null) {
    try {
      const data = {
        value: value,
        timestamp: Date.now(),
        ttl: ttlMs,
        sessionKey: this.sessionKey
      };

      const encrypted = this.encrypt(data);
      if (encrypted) {
        localStorage.setItem(`secure_${key}`, encrypted);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Secure storage set failed:', error);
      return false;
    }
  }

  /**
   * Secure get operation with TTL validation
   */
  get(key) {
    try {
      const encryptedData = localStorage.getItem(`secure_${key}`);
      if (!encryptedData) return null;

      const decrypted = this.decrypt(encryptedData);
      if (!decrypted) return null;

      // Validate session key
      if (decrypted.sessionKey !== this.sessionKey) {
        this.clear(key); // Clear invalid session data
        return null;
      }

      // Check TTL
      if (decrypted.ttl && Date.now() - decrypted.timestamp > decrypted.ttl) {
        this.clear(key); // Clear expired data
        return null;
      }

      return decrypted.value;
    } catch (error) {
      console.error('Secure storage get failed:', error);
      return null;
    }
  }

  /**
   * Clear specific key
   */
  clear(key) {
    try {
      localStorage.removeItem(`secure_${key}`);
      return true;
    } catch (error) {
      console.error('Secure storage clear failed:', error);
      return false;
    }
  }

  /**
   * Clear all secure storage
   */
  clearAll() {
    try {
      const keys = Object.keys(localStorage).filter(key => key.startsWith('secure_'));
      keys.forEach(key => localStorage.removeItem(key));
      return true;
    } catch (error) {
      console.error('Secure storage clear all failed:', error);
      return false;
    }
  }

  /**
   * Check if key exists and is valid
   */
  has(key) {
    return this.get(key) !== null;
  }

  /**
   * Get storage metadata
   */
  getMetadata(key) {
    try {
      const encryptedData = localStorage.getItem(`secure_${key}`);
      if (!encryptedData) return null;

      const decrypted = this.decrypt(encryptedData);
      if (!decrypted) return null;

      return {
        timestamp: decrypted.timestamp,
        ttl: decrypted.ttl,
        expired: decrypted.ttl ? Date.now() - decrypted.timestamp > decrypted.ttl : false
      };
    } catch (error) {
      return null;
    }
  }

  /**
   * Session-specific secure storage (clears on tab close)
   */
  setSession(key, value) {
    try {
      const sessionData = {
        value: value,
        timestamp: Date.now(),
        isSession: true
      };

      const encrypted = this.encrypt(sessionData);
      if (encrypted) {
        sessionStorage.setItem(`secure_${key}`, encrypted);
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  getSession(key) {
    try {
      const encryptedData = sessionStorage.getItem(`secure_${key}`);
      if (!encryptedData) return null;

      const decrypted = this.decrypt(encryptedData);
      return decrypted ? decrypted.value : null;
    } catch (error) {
      return null;
    }
  }

  clearSession(key) {
    try {
      sessionStorage.removeItem(`secure_${key}`);
      return true;
    } catch (error) {
      return false;
    }
  }
}

// Create singleton instance
const secureStorage = new SecureStorage();

// Export convenience methods for specific data types
export const authTokenStorage = {
  set: (token) => secureStorage.set('authToken', token, 3600000), // 1 hour TTL
  get: () => secureStorage.get('authToken'),
  clear: () => secureStorage.clear('authToken'),
  has: () => secureStorage.has('authToken')
};

export const userProfileStorage = {
  set: (profile) => secureStorage.set('userProfile', profile, 3600000), // 1 hour TTL
  get: () => secureStorage.get('userProfile'),
  clear: () => secureStorage.clear('userProfile'),
  has: () => secureStorage.has('userProfile')
};

export const sessionStorage = {
  set: (data) => secureStorage.setSession('sessionData', data),
  get: () => secureStorage.getSession('sessionData'),
  clear: () => secureStorage.clearSession('sessionData')
};

export default secureStorage;
