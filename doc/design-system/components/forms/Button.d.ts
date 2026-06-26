import { Button } from './Button.jsx';

export interface ButtonProps {
  /**
   * Button label text
   */
  children: React.ReactNode;

  /**
   * Visual variant
   */
  variant?: 'primary' | 'secondary' | 'ghost';

  /**
   * Size preset
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Disabled state
   */
  disabled?: boolean;

  /**
   * Click handler
   */
  onClick?: () => void;

  /**
   * HTML button type
   */
  type?: 'button' | 'submit' | 'reset';
}

export default Button;
