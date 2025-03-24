import React from 'react';
import { Tag as TagType } from '@/types';

interface TagProps {
  tag: TagType;
  size?: 'small' | 'normal';
  onClick?: () => void;
}

const Tag: React.FC<TagProps> = ({ tag, size = 'normal', onClick }) => {
  return (
    <span
      className={`
        inline-flex items-center rounded transition-colors
        ${size === 'small' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm'}
        ${onClick ? 'cursor-pointer hover:opacity-80' : ''}
      `}
      style={{
        backgroundColor: `${tag.color}20`,
        color: tag.color,
        borderColor: `${tag.color}40`,
      }}
      onClick={onClick}
    >
      {tag.name}
    </span>
  );
};

export default Tag;
