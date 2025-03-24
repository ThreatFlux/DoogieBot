import React from 'react';

interface SkeletonProps {
  /**
   * The width of the skeleton
   */
  width?: string | number;
  /**
   * The height of the skeleton
   */
  height?: string | number;
  /**
   * Whether the skeleton is rounded
   */
  rounded?: boolean;
  /**
   * Whether the skeleton is a circle
   */
  circle?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
  /**
   * Number of skeleton items to render in a group
   */
  count?: number;
  /**
   * Gap between multiple skeletons when count > 1
   */
  gap?: string;
  /**
   * Whether to animate the skeleton
   */
  animate?: boolean;
  /**
   * Whether skeleton represents text line(s)
   */
  text?: boolean;
  /**
   * For text skeletons, how many lines to show
   */
  lines?: number;
  /**
   * For text skeletons, whether to vary the widths to look more natural
   */
  varyingWidths?: boolean;
}

/**
 * Skeleton component for representing loading content
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  rounded = true,
  circle = false,
  className = '',
  count = 1,
  gap = '0.5rem',
  animate = true,
  text = false,
  lines = 3,
  varyingWidths = true,
}) => {
  // Base classes for the skeleton
  const baseClasses = [
    'bg-gray-200 dark:bg-gray-700',
    animate ? 'animate-pulse' : '',
    rounded && !circle ? 'rounded-md' : '',
    circle ? 'rounded-full' : '',
    className,
  ].join(' ');

  // Generate inline styles
  const getStyle = (index: number) => {
    const styles: React.CSSProperties = {};
    
    // Width handling
    if (width) {
      styles.width = typeof width === 'number' ? `${width}px` : width;
    } else if (text && varyingWidths && !circle) {
      // For text lines, create varied widths for a more natural look
      const lineIndex = index % lines;
      const widthVariations = ['100%', '92%', '88%', '95%', '80%'];
      styles.width = widthVariations[lineIndex % widthVariations.length];
    }
    
    // Height handling
    if (height) {
      styles.height = typeof height === 'number' ? `${height}px` : height;
    } else if (text && !circle) {
      styles.height = '1rem'; // Default text line height
    }
    
    // For circular skeletons, ensure equal width and height
    if (circle && width) {
      styles.height = styles.width;
    }
    
    return styles;
  };

  // For text content, show multiple lines with varying widths
  if (text) {
    return (
      <div className="flex flex-col" style={{ gap }}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={baseClasses}
            style={getStyle(i)}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  // Render the requested number of skeleton elements
  if (count > 1) {
    return (
      <div className="flex flex-col" style={{ gap }}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className={baseClasses}
            style={getStyle(i)}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  // Render a single skeleton element
  return (
    <div
      className={baseClasses}
      style={getStyle(0)}
      aria-hidden="true"
    />
  );
};

/**
 * Avatar placeholder skeleton
 */
export const AvatarSkeleton: React.FC<{ size?: number }> = ({ size = 40 }) => (
  <Skeleton circle width={size} height={size} />
);

/**
 * Text line placeholder skeleton
 */
export const TextSkeleton: React.FC<{ lines?: number, width?: string }> = ({ 
  lines = 1, 
  width = '100%' 
}) => (
  <Skeleton text lines={lines} width={width} />
);

/**
 * Card placeholder skeleton
 */
export const CardSkeleton: React.FC<{ lines?: number }> = ({ lines = 3 }) => (
  <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
    <div className="mb-4">
      <Skeleton height={24} width="60%" />
    </div>
    <div className="space-y-2">
      <TextSkeleton lines={lines} />
    </div>
    <div className="mt-4 flex justify-between">
      <Skeleton width={80} height={32} />
      <Skeleton width={80} height={32} />
    </div>
  </div>
);

/**
 * Button placeholder skeleton
 */
export const ButtonSkeleton: React.FC<{ width?: number }> = ({ width = 120 }) => (
  <Skeleton width={width} height={40} />
);

/**
 * Image placeholder skeleton
 */
export const ImageSkeleton: React.FC<{ width?: number | string, height?: number | string }> = ({ 
  width = '100%', 
  height = 200 
}) => (
  <Skeleton width={width} height={height} />
);

export default Skeleton;
