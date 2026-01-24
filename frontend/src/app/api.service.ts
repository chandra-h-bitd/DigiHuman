import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Session {
  session_id: string;
  session_name: string;
  primary_llm: string;
  created_at: string;
  last_activity: string;
  document_count: number;
  conversation_count: number;
}

export interface Document {
  document_id: string;
  session_id: string;
  file_name: string;
  file_type: string;
  file_path: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface Conversation {
  conversation_id: string;
  session_id: string;
  query: string;
  response: string;
  llm_used: string;
  sources: any[];
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  session_id: string;
  file_name: string;
  chunks_indexed: number;
  used_fallback: boolean;
  embed_provider: string;
}

export interface QueryResponse {
  conversation_id: string;
  answer: string;
  sources: any[];
  llm_used: string;
  llm_model: string;
  embed_provider: string;
  embedding_model: string;
  embedding_fallback: boolean;
  generation_fallback: boolean;
  used_fallback: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8001';

  constructor(private http: HttpClient) {}

  // ========== Session Management ==========

  createSession(sessionName: string, primaryLlm: string = 'chatgpt'): Observable<Session> {
    return this.http.post<Session>(`${this.baseUrl}/sessions`, {
      session_name: sessionName,
      primary_llm: primaryLlm
    });
  }

  listSessions(): Observable<Session[]> {
    return this.http.get<Session[]>(`${this.baseUrl}/sessions`);
  }

  getSession(sessionId: string): Observable<Session> {
    return this.http.get<Session>(`${this.baseUrl}/sessions/${sessionId}`);
  }

  updateSession(sessionId: string, updates: { session_name?: string; primary_llm?: string }): Observable<any> {
    return this.http.put(`${this.baseUrl}/sessions/${sessionId}`, updates);
  }

  deleteSession(sessionId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/sessions/${sessionId}`);
  }

  // ========== Document Management ==========

  uploadDocument(sessionId: string, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post(`${this.baseUrl}/sessions/${sessionId}/upload`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  listDocuments(sessionId: string): Observable<Document[]> {
    return this.http.get<Document[]>(`${this.baseUrl}/sessions/${sessionId}/documents`);
  }

  // ========== Query / Conversation ==========

  query(sessionId: string, question: string): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.baseUrl}/sessions/${sessionId}/query`, {
      question: question
    });
  }

  getConversations(sessionId: string, limit?: number): Observable<Conversation[]> {
    let params = new HttpParams();
    if (limit) {
      params = params.set('limit', limit.toString());
    }
    return this.http.get<Conversation[]>(`${this.baseUrl}/sessions/${sessionId}/conversations`, { params });
  }

  // ========== Configuration / API Keys ==========

  setConfig(keyName: string, keyValue: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/config`, {
      key_name: keyName,
      key_value: keyValue
    });
  }

  getConfig(keyName: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/config/${keyName}`);
  }

  getAllConfig(): Observable<any> {
    return this.http.get(`${this.baseUrl}/config`);
  }

  deleteConfig(keyName: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/config/${keyName}`);
  }

  // ========== Diagnostics ==========

  getSessionDiagnostics(sessionId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/sessions/${sessionId}/diagnostics`);
  }

  health(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health`);
  }
}
