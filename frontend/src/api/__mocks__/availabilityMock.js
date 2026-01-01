// Mock data for availability
let mockAvailability = {
  "123": {
    slots: [
      "Monday-09:00",
      "Monday-10:00",
      "Monday-11:00",
      "Tuesday-14:00",
      "Tuesday-15:00",
      "Wednesday-10:00",
      "Wednesday-11:00",
      "Wednesday-12:00",
      "Friday-13:00",
      "Friday-14:00",
      "Friday-15:00"
    ],
    customPreference: false,
    is_recurring: true,
    lastUpdated: new Date().toISOString()
  }
};

// Load from localStorage if available
const loadFromStorage = () => {
  try {
    const saved = localStorage.getItem("mock-availability");
    if (saved) {
      mockAvailability = JSON.parse(saved);
    }
  } catch (e) {
    console.error("Failed to load mock data from localStorage", e);
  }
};

// Save to localStorage
const saveToStorage = () => {
  try {
    localStorage.setItem("mock-availability", JSON.stringify(mockAvailability));
  } catch (e) {
    console.error("Failed to save mock data to localStorage", e);
  }
};

// Load initial data
loadFromStorage();

// Mock GET /availability/:userId
export const getAvailability = userId => {
  return new Promise(resolve => {
    // Simulate network delay
    setTimeout(() => {
      loadFromStorage(); // Always get fresh data from storage
      
      if (mockAvailability[userId]) {
        resolve({
          data: {
            slots: mockAvailability[userId].slots || [],
            customPreference: mockAvailability[userId].customPreference || false,
            is_recurring: mockAvailability[userId].is_recurring !== undefined 
              ? mockAvailability[userId].is_recurring 
              : true // Default to true if not set
          },
          status: 200
        });
      } else {
        // Initialize empty data for new users
        mockAvailability[userId] = {
          slots: [],
          customPreference: false,
          is_recurring: true,
          lastUpdated: new Date().toISOString()
        };
        saveToStorage();
        
        resolve({
          data: { 
            slots: [], 
            customPreference: false,
            is_recurring: true 
          },
          status: 200
        });
      }
    }, 300);
  });
};

// Mock POST /availability/:userId
export const updateAvailability = (userId, data) => {
  return new Promise(resolve => {
    // Simulate network delay
    setTimeout(() => {
      mockAvailability[userId] = {
        slots: Array.isArray(data.slots) ? data.slots : [],
        customPreference: data.customPreference || false,
        is_recurring: data.is_recurring !== undefined ? data.is_recurring : true,
        lastUpdated: new Date().toISOString()
      };
      
      saveToStorage();
      
      resolve({
        data: { 
          success: true, 
          message: "Availability updated successfully",
          data: mockAvailability[userId]
        },
        status: 200
      });
    }, 300);
  });
};

export default {
  getAvailability,
  updateAvailability
};
