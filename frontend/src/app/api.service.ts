import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ProviderConfig {
  provider: string;
  apiKey: string;
  embeddingModel?: string;
  generationModel?: string;
}

export interface ModelsResponse {
  provider: string;
  embedding_model?: string;
  generation_model?: string;
  available_models: {
    embedding: string[];
    generation: string[];
  };
  api_valid: boolean;
  error_message?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  backendUrl = 'http://localhost:8000';
  constructor(private http: HttpClient) {}

  upload(file: File, sessionId?: string, config?: ProviderConfig): Observable<HttpEvent<any>> {
    const form = new FormData();
    form.append('file', file);
    if (sessionId) form.append('session_id', sessionId);
    if (config) {
      form.append('provider', config.provider);
      if (config.apiKey) form.append('api_key', config.apiKey);
      if (config.embeddingModel) form.append('embedding_model', config.embeddingModel);
      if (config.generationModel) form.append('generation_model', config.generationModel);
    }
    return this.http.post(`${this.backendUrl}/upload`, form, { observe: 'events', reportProgress: true });
  }

  ask(sessionId: string, question: string, config?: ProviderConfig, k: number = 5) {
    const body: any = { 
      session_id: sessionId, 
      question, 
      k
    };
    if (config) {
      body.provider = config.provider;
      body.api_key = config.apiKey || null;
      body.embedding_model = config.embeddingModel || null;
      body.generation_model = config.generationModel || null;
    }
    return this.http.post(`${this.backendUrl}/ask`, body);
  }

  models(provider: string = 'gemini', apiKey?: string): Observable<ModelsResponse> {
    const params: any = { provider };
    if (apiKey) params.api_key = apiKey;
    return this.http.get<ModelsResponse>(`${this.backendUrl}/models`, { params });
  }

  validateProvider(config: ProviderConfig): Observable<ModelsResponse> {
    return this.http.post<ModelsResponse>(`${this.backendUrl}/validate`, {
      provider: config.provider,
      api_key: config.apiKey,
      embedding_model: config.embeddingModel || null,
      generation_model: config.generationModel || null
    });
  }
}
