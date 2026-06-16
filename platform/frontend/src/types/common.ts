export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiErrorResponse {
  title: string;
  detail: string;
  status: number;
  type?: string;
}
