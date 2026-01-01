import { useNavigate } from 'react-router-dom';
import { useContext } from 'react';
import { LanguageContext } from './lib/LanguageContext';

export default function AvailabilityRequiredDialog({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { t } = useContext(LanguageContext);

  const handleOkClick = () => {
    onClose();
    navigate('/schedule');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">{t('availabilityRequiredDialog.title')}</h3>
        <p className="mb-6 text-gray-700 dark:text-gray-300">
          {t('availabilityRequiredDialog.description')}
        </p>
        <div className="flex justify-end">
          <button
            onClick={handleOkClick}
            className="px-4 py-2 bg-teal-500 dark:bg-teal-600 text-white rounded-md hover:bg-teal-600 dark:hover:bg-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors duration-200"
            autoFocus
          >
            {t('availabilityRequiredDialog.goToSchedule')}
          </button>
        </div>
      </div>
    </div>
  );
}
