import { useCallback } from 'react';
import { apiService } from '@/api/apiService';

export const useCheckGames = () => {
  const checkGames = useCallback(async () => {
    try {
      const response = await apiService.get('/user_game_preferences/');
      return response.data && response.data.length > 0;
    } catch (error) {
      console.error('Error checking user games:', error);
      return false;
    }
  }, []);

  return { checkGames };
};
