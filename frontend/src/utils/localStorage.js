export class LocalStorageItem {
  constructor(key) {
    this.key = key;
  }

  get() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(this.key);
      }
      return null;
    } catch (error) {
      console.error(`Error getting localStorage item "${this.key}":`, error);
      return null;
    }
  }

  set(value) {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.setItem(this.key, value);
      }
    } catch (error) {
      console.error(`Error setting localStorage item "${this.key}":`, error);
    }
  }

  clear() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.removeItem(this.key);
      }
    } catch (error) {
      console.error(`Error clearing localStorage item "${this.key}":`, error);
    }
  }
}

const authToken = new LocalStorageItem("authToken");
const authUserId = new LocalStorageItem("authUserId");
const authisLoggedIn = new LocalStorageItem("authisLoggedIn");
const isDiscordRegistered = new LocalStorageItem("isDiscordRegistered");

export default {
  authToken,
  authUserId,
  authisLoggedIn,
  isDiscordRegistered
};
