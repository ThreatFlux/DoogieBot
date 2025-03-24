import React from 'react';

export type FeedbackType = 'positive' | 'negative';

interface FeedbackButtonProps {
  messageId: string;
  type: FeedbackType;
  label: string;
  onClick: () => void;
  icon: React.ReactNode;
}

const FeedbackButton: React.FC<FeedbackButtonProps> = ({
  messageId,
  type,
  label,
  onClick,
  icon
}) => (
  <button
    onClick={onClick}
    className={`p-1 ${
      type === 'positive'
        ? 'text-green-500 hover:bg-green-100 dark:hover:bg-green-900/30'
        : 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30'
    } rounded`}
    title={label}
  >
    {icon}
  </button>
);

export default FeedbackButton;
