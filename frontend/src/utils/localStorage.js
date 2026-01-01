export class LocalStorageItem {
  constructor(key) {
    this.key = key;
  }
  get() {
    return localStorage.getItem(this.key);
  }
  set(value) {
    return localStorage.setItem(this.key, value);
  }
  clear() {
    return localStorage.removeItem(this.key);
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
