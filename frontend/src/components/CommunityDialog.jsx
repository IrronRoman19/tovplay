import { useState, useContext } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { apiService } from "@/api/apiService";
import { LanguageContext } from "@/components/lib/LanguageContext";

export function CommunityDialog({ isOpen, onClose, discordInviteLink }) {
  const { t, language } = useContext(LanguageContext);
  const [isChecking, setIsChecking] = useState(false);
  const [joinMessage, setJoinMessage] = useState('');
  const isRtl = language === "he";
  const MAX_RETRIES = 3;

  const checkStatus = async (attempt = 1) => {
    try {
      console.log('Checking community status, attempt:', attempt);
      const response = await apiService.checkCommunityStatus();
      console.log('Community status response:', response);
      
      // Check if there's an error in the response
      if (response.error) {
        console.log('Response contains error:', response.error);
        // If user is not connected with Discord, no point in retrying
        if (response.error.includes('not connected with Discord')) {
          setJoinMessage(t('community.connectDiscordFirst'));
          setIsChecking(false);
          return;
        }
        
        if (attempt < MAX_RETRIES) {
          // Retry after a delay
          setJoinMessage(t('community.retryConnecting', { attempt, max: MAX_RETRIES }));
          setTimeout(() => checkStatus(attempt + 1), 2000);
          return;
        }
        throw new Error(response.error);
      }
      
      // Check if user is in community
      const isInCommunity = response.in_community === true || 
                     response.in_community === 'true' || 
                     response.in_community === null; // Add this line
      console.log('isInCommunity:', isInCommunity);
      
    // And update the message to show the actual value for debugging:
    console.log('Community status raw response:', {
      in_community: response.in_community,
      type: typeof response.in_community,
      fullResponse: response
    });

      if (isInCommunity) {
        // If already in community, update the UI and close the dialog
        setJoinMessage(t('community.welcomeMessage'));
        
        // Close the dialog after a short delay
        setTimeout(() => {
          onClose();
          // Reload the page to update the UI
          window.location.reload();
        }, 1500);
      } else if (attempt < MAX_RETRIES) {
        // If not in community but have retries left, try again
        setJoinMessage(t('community.checkingStatus', { attempt, max: MAX_RETRIES }));
        setTimeout(() => checkStatus(attempt + 1), 2000);
      } else {
        // If max retries reached and still not in community
        setJoinMessage(t('community.completeJoinProcess'));
        setIsChecking(false);
      }
    } catch (error) {
      console.error('Error checking community status (attempt', attempt, '):', error);
      if (attempt < MAX_RETRIES) {
        // Retry on error
        setJoinMessage(t('community.retryConnecting', { attempt, max: MAX_RETRIES }));
        setTimeout(() => checkStatus(attempt + 1), 2000); // 2 second delay
      } else {
        setJoinMessage(t('community.errorCheckingStatus'));
        setIsChecking(false);
      }
    }
  };

  const handleJoinCommunity = async () => {
    if (!discordInviteLink) return;
    
    // Show loading state
    setIsChecking(true);
    setJoinMessage(t('community.openingDiscord'));
    
    try {
      // First, try to update the community status
      await apiService.setInCommunityTrue();
      console.log('Successfully updated community status');
      
      // Then open Discord in a new tab
      window.open(discordInviteLink, "_blank", "noopener,noreferrer");
      
      // Start checking status after a short delay to give Discord time to load
      setTimeout(() => {
        setJoinMessage(t('community.checkingCommunityStatus'));
        // Start checking status with retries
        checkStatus(1);
      }, 2000);
    } catch (error) {
      console.error('Error updating community status:', error);
      // Still open Discord even if there was an error updating status
      window.open(discordInviteLink, "_blank", "noopener,noreferrer");
      setJoinMessage(t('community.joinAndVerify'));
      setIsChecking(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className={`sm:max-w-[425px] ${isRtl ? 'text-right' : 'text-left'}`}>
        <DialogHeader className={isRtl ? 'text-right' : 'text-left'}>
          <DialogTitle className={isRtl ? 'text-right' : 'text-left'}>{t('community.joinTitle')}</DialogTitle>
          <DialogDescription className={`space-y-2 ${isRtl ? 'text-right' : 'text-left'}`}>
            <p className={isRtl ? 'text-right' : 'text-left'}>{t('community.joinDescription')}</p>
            {joinMessage && (
              <p className={`text-sm text-foreground/80 bg-muted/50 p-2 rounded-md ${isRtl ? 'text-right' : 'text-left'}`}>
                {joinMessage}
              </p>
            )}
            <p className={`text-sm text-muted-foreground ${isRtl ? 'text-right' : 'text-left'}`}>
              {t('community.alreadyJoined')}
            </p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className={`gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
          <Button 
            onClick={onClose} 
            variant="outline"
            className="border-teal-500 text-teal-600 hover:bg-teal-50 hover:text-teal-700"
          >
            {t('common.maybeLater')}
          </Button>
          <Button 
            onClick={handleJoinCommunity}
            className="bg-teal-600 hover:bg-teal-700 text-white"
            disabled={isChecking}
          >
            {isChecking ? (
              <>
                <Loader2 className={`h-4 w-4 animate-spin ${isRtl ? 'ml-2' : 'mr-2'}`} />
                {t('common.verifying')}
              </>
            ) : (
              t('community.joinButton')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
