declare module 'react-window' {
  import * as React from 'react';

  export interface ListChildComponentProps {
    index: number;
    style: React.CSSProperties;
  }

  export interface FixedSizeListProps {
    children: React.ComponentType<ListChildComponentProps>;
    className?: string;
    height: number;
    itemCount: number;
    itemSize: number;
    width: number | string;
  }

  export class FixedSizeList extends React.Component<FixedSizeListProps> {}
}