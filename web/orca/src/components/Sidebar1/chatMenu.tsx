import React from 'react';
import ReactDOM from 'react-dom';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  message: string;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ isOpen, onClose, onConfirm, message }) => {
  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="bg-slate-500 rounded-lg p-6 max-w-sm w-full">
        <h2 className="text-xl font-bold text-white mb-4">Confirm Action</h2>
        <p className="text-white mb-6">{message}</p>
        <div className="flex justify-end space-x-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-slate-300 rounded hover:bg-gray-700 transition-colors"
          >
            No
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-slate-300 rounded hover:bg-red-700 transition-colors"
          >
            Yes
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ConfirmationModal;