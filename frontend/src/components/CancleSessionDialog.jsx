import { Button } from "@/components/ui/button";
import { MultilineInput } from "@/components/ui/MultilineInput";
import React, { useContext } from "react";
import { LanguageContext } from "@/components/lib/LanguageContext";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function CancelSessionDialog({ isOpen, onClose, onSend, session }) {
  const { t } = useContext(LanguageContext);

  const inputRef = React.useRef(null);
  const [isDisabled, setIsDisabled] = React.useState(false);
  if(!session){
    return null;
  }
  async function sendMessage() {
    try{
      setIsDisabled(true);
    const message = inputRef.current.value;
    await onSend(message);
    } catch (error){
      console.error("Error sending cancel message:", error);
    }
    finally{
      setIsDisabled(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t('cancelSession.title')}</DialogTitle>
          <DialogDescription>
            {t('cancelSession.description', { date: session["scheduled_date"], time: session.start_time.substring(0,5) })}
          </DialogDescription>
        </DialogHeader>
          {t('cancelSession.messagePrompt', { 
            participants: session['participants'].join(", "), 
            game: session['game_name'] 
          })}
          <MultilineInput
            className="w-full h-32 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
            placeholder={t('cancelSession.placeholder')}
            ref={inputRef}
          />
        <DialogFooter className="gap-3">
          <Button 
            onClick={onClose} 
            variant="outline"
            className="border-teal-500 text-teal-600 hover:bg-teal-50 hover:text-teal-700"
          >
            {t('cancel')}
          </Button>
          <Button 
            onClick={sendMessage}
            className="bg-teal-600 hover:bg-teal-700 text-white"
            disabled={isDisabled}
          >
            {t('send')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
