import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { HttpEventType } from '@angular/common/http';
import { ApiService } from './api.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: any[];
  fallback?: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressBarModule, MatCardModule, MatChipsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Document Q&A';
  backendUrl = 'http://localhost:8000';

  geminiKey = '';
  sessionId = '';

  uploadProgress = 0;
  embeddingFallback = false;

  question = '';
  messages: ChatMessage[] = [];

  uploading = false;
  answering = false;

  constructor(private api: ApiService) {}

  updateKey(key: string) {
    this.geminiKey = key;
  }

  async uploadFile(event: any) {
    const file = event.target.files[0];
    if (!file) return;

    const form = new FormData();
    form.append('file', file);
    if (this.sessionId) form.append('session_id', this.sessionId);
    if (this.geminiKey) form.append('gemini_api_key', this.geminiKey);

    this.uploading = true;
    this.uploadProgress = 0;

    this.api.upload(file, this.sessionId, this.geminiKey)
      .subscribe({
        next: (event: any) => {
          if (event.type === HttpEventType.UploadProgress) {
            this.uploadProgress = Math.round(100 * event.loaded / (event.total || event.loaded));
          } else if (event.type === HttpEventType.Response) {
            const data = event.body;
            this.sessionId = data.session_id;
            this.embeddingFallback = data.used_fallback;
            this.uploading = false;
          }
        },
        error: (err) => {
          console.error(err);
          this.uploading = false;
        }
      });
  }

  ask() {
    const q = this.question.trim();
    if (!q) return;
    this.messages.push({ role: 'user', text: q });
    this.answering = true;

    const body = { session_id: this.sessionId, question: q, k: 5, gemini_api_key: this.geminiKey || null };
    this.api.ask(this.sessionId, q, this.geminiKey).subscribe({
      next: (data: any) => {
        this.messages.push({ role: 'assistant', text: data.answer, sources: data.sources, fallback: data.used_fallback });
        this.question = '';
        this.answering = false;
      },
      error: (err) => {
        console.error(err);
        this.messages.push({ role: 'assistant', text: 'Error generating answer.' });
        this.answering = false;
      }
    });
  }

  getModels() {
    const params: any = {};
    if (this.geminiKey) params.gemini_api_key = this.geminiKey;
    this.api.models(this.geminiKey).subscribe(console.log);
  }
}
