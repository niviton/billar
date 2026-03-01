
import { Product, AppSettings } from './types';

export const DEFAULT_PRODUCTS: Product[] = [
  { id: '1', name: 'X-Burger Clássico', category: 'Hambúrgueres', price: 18.9, stock: 50, icon: '🍔' },
  { id: '2', name: 'X-Bacon Especial', category: 'Hambúrgueres', price: 22.9, stock: 30, icon: '🍔' },
  { id: '3', name: 'X-Tudo Supreme', category: 'Hambúrgueres', price: 28.9, stock: 20, icon: '🍔' },
  { id: '4', name: 'Hot Dog Completo', category: 'Lanches', price: 12.9, stock: 40, icon: '🌭' },
  { id: '5', name: 'Misto Quente', category: 'Lanches', price: 8.9, stock: 60, icon: '🥪' },
  { id: '6', name: 'Batata Frita Grande', category: 'Porções', price: 15.9, stock: 100, icon: '🍟' },
  { id: '7', name: 'Onion Rings', category: 'Porções', price: 14.9, stock: 80, icon: '🧅' },
  { id: '8', name: 'Refrigerante Lata', category: 'Bebidas', price: 5.9, stock: 200, icon: '🥤' },
  { id: '9', name: 'Suco Natural', category: 'Bebidas', price: 8.9, stock: 50, icon: '🧃' },
  { id: '10', name: 'Milkshake', category: 'Sobremesas', price: 12.9, stock: 30, icon: '🥤' },
];

export const DEFAULT_SETTINGS: AppSettings = {
  storeName: 'Billá Burger',
  slogan: 'Os melhores hambúrgueres da cidade!',
  font: 'Google Sans',
  fontSize: 16,
  colors: {
    background: '#f8f9fa',
    surface: '#ffffff',
    text: '#1e293b',
    primary: '#ef4444', // Vermelho
    secondary: '#fbbf24', // Amarelo
  }
};
