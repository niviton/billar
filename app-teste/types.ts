
export type UserRole = 'garcom' | 'cozinha' | 'gerente';

export interface User {
  id: string;
  username: string;
  password?: string;
  role: UserRole;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  icon: string; // Pode ser um Emoji ou uma URL/Base64 de imagem
  isImage?: boolean; // Flag para saber se renderiza como img ou texto
}

export interface OrderItem {
  id: string;
  name: string;
  price: number;
  qty: number;
  icon: string;
  isImage?: boolean;
}

export type OrderStatus = 'cozinha' | 'pronto' | 'finalizado' | 'cancelado';

export type OrderType = 'dine-in' | 'delivery';

export interface Order {
  id: string;
  mesa: string;
  cliente: string;
  items: OrderItem[];
  observacoes: string;
  total: number;
  status: OrderStatus;
  timestamp: number;
  waiterId: string;
  pagamento?: string;
  orderType?: OrderType;
  address?: string; // Novo campo para separar o endereço da observação
}

export interface AppSettings {
  storeName: string;
  slogan: string;
  logo?: string; // Novo campo para logo da loja
  font: string;
  fontSize: number;
  colors: {
    background: string;
    surface: string;
    text: string;
    primary: string;
    secondary: string;
  };
}

// Interfaces auxiliares para relatórios
export interface WaiterStats {
  id: string;
  name: string;
  totalSales: number;
  ordersCount: number;
  averageTicket: number;
}

export interface Suggestion {
  title: string;
  description: string;
  genre: string;
  bpm: number;
}

export interface LyricsResponse {
  lyrics: string;
  mood: string;
}

export interface Track {
  id: string;
  type: string;
  name: string;
  isActive: boolean;
  color: string;
}
