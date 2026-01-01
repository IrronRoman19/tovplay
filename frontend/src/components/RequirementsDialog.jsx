import { useNavigate } from 'react-router-dom';
import { useContext } from 'react';
import { LanguageContext } from './lib/LanguageContext';

export default function RequirementsDialog({ 
  isOpen, 
  onClose, 
  missingAvailability, 
  missingGames 
}) {
  const navigate = useNavigate();
  const { t } = useContext(LanguageContext);

  const handleScheduleClick = () => {
    onClose();
    navigate('/schedule');
  };

  const handleProfileClick = () => {
    onClose();
    navigate('/myprofile');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {t('requirementsDialog.title')}
        </h3>
        
        {missingAvailability && (
          <p className="mb-4 text-gray-700 dark:text-gray-300">
            ❌ {t('requirementsDialog.missingAvailability')}
          </p>
        )}
        
        {missingGames && (
          <p className="mb-4 text-gray-700 dark:text-gray-300">
            ❌ {t('requirementsDialog.missingGames')}
          </p>
        )}

        <div className="flex justify-end gap-x-3 mt-6">
          {missingAvailability && (
            <button
              onClick={handleScheduleClick}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-600 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors duration-200"
            >
              {t('requirementsDialog.setAvailability')}
            </button>
          )}
          
          {missingGames && (
            <button
              onClick={handleProfileClick}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-600 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors duration-200"
            >
              {t('requirementsDialog.addGames')}
            </button>
          )}
          
          {/* <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 transition-colors duration-200"
          >
            {t('requirementsDialog.close')}
          </button> */}
        </div>
      </div>
    </div>
  );
}
