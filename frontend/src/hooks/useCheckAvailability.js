import { useCallback } from 'react';
import { apiService } from '@/api/apiService';

export const useCheckAvailability = () => {
  const checkAvailability = useCallback(async () => {
    try {
      const response = await apiService.get('/availability/');
      return response.data && (response.data.slots?.length > 0 || response.data.length > 0);
    } catch (error) {
      console.error('Error checking availability:', error);
      return false;
    }
  }, []);

  return { checkAvailability };
};
