import { Card } from './Card.jsx';

export interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'elevated';
  elevation?: 1 | 2 | 3 | 4;
}

export default Card;
