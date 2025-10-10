import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  backendUrl = this.getBackendUrl();
  
  constructor(private http: HttpClient) {}

  private getBackendUrl(): string {
    // Auto-detect environment
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'; // Local development
    }
    return '/api'; // Deployed (Vercel)
  }

  upload(file: File, sessionId?: string, geminiKey?: string): Observable<HttpEvent<any>> {
    const form = new FormData();
    form.append('file', file);
    if (sessionId) form.append('session_id', sessionId);
    if (geminiKey) form.append('gemini_api_key', geminiKey);
    return this.http.post(`${this.backendUrl}/upload`, form, { observe: 'events', reportProgress: true });
  }

  ask(sessionId: string, question: string, geminiKey?: string, k: number = 5) {
    return this.http.post(`${this.backendUrl}/ask`, { session_id: sessionId, question, k, gemini_api_key: geminiKey || null });
  }

  models(geminiKey?: string) {
    const params: any = {};
    if (geminiKey) params.gemini_api_key = geminiKey;
    return this.http.get(`${this.backendUrl}/models`, { params });
  }
}
