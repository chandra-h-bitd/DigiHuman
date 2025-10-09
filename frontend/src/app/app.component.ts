import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TextFieldModule } from '@angular/cdk/text-field';
import { HttpEventType } from '@angular/common/http';
import { ApiService } from './api.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: any[];
  fallback?: boolean;
  ts?: Date;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule, MatProgressBarModule, MatCardModule, MatChipsModule, MatSnackBarModule, MatTooltipModule, MatProgressSpinnerModule, TextFieldModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Document Q&A';
  backendUrl = 'http://localhost:8000';

  geminiKey = '';
  sessionId = '';
  keyVisible = false;
  keyStatus: 'not_configured' | 'checking' | 'valid' | 'invalid' = 'not_configured';
  embeddingModel?: string;
  generationModel?: string;
  availableModels: string[] = [];
  apiCollapsed = false;

  uploadProgress = 0;
  embeddingFallback = false;
  uploadedFile?: { name: string; size: number };
  dragOver = false;
  uploadCollapsed = false;

  question = '';
  messages: ChatMessage[] = [];

  uploading = false;
  answering = false;

  suggestedQuestions: string[] = [
    'Summarize this document in 3 bullet points.',
    'What are the key takeaways?',
    'List any dates, amounts, or deadlines mentioned.',
    'Who are the main stakeholders and their roles?'
  ];

  sidebarOpen = true; // for mobile

  constructor(private api: ApiService, private snack: MatSnackBar, private sanitizer: DomSanitizer) {}

  updateKey(key: string) {
    this.geminiKey = key;
  }

  async uploadFile(event: any) {
    const file = event.target.files[0];
    if (!file) return;

    if (!/\.(pdf|docx)$/i.test(file.name)) {
      this.snack.open('Only PDF and DOCX files are supported.', 'Dismiss', { duration: 3000 });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.snack.open('File too large. Max 10MB allowed.', 'Dismiss', { duration: 3000 });
      return;
    }

    const form = new FormData();
    form.append('file', file);
    if (this.sessionId) form.append('session_id', this.sessionId);
    if (this.geminiKey) form.append('gemini_api_key', this.geminiKey);

    this.uploading = true;
    this.uploadProgress = 0;
    this.uploadedFile = { name: file.name, size: file.size };

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
            this.snack.open(`Uploaded • ${this.uploadedFile?.name}`, 'OK', { duration: 2500 });
            this.uploadCollapsed = true;
          }
        },
        error: (err) => {
          console.error(err);
          this.uploading = false;
          this.uploadedFile = undefined;
          this.snack.open('Upload failed. Please try again.', 'Dismiss', { duration: 3000 });
        }
      });
  }

  ask() {
    const q = this.question.trim();
    if (!q) return;
    this.messages.push({ role: 'user', text: q, ts: new Date() });
    this.answering = true;

    const body = { session_id: this.sessionId, question: q, k: 5, gemini_api_key: this.geminiKey || null };
    this.api.ask(this.sessionId, q, this.geminiKey).subscribe({
      next: (data: any) => {
        this.messages.push({ role: 'assistant', text: data.answer, sources: data.sources, fallback: data.used_fallback, ts: new Date() });
        this.question = '';
        this.answering = false;
        if (data.used_fallback) {
          this.snack.open('Answer generated with fallback.', 'Info', { duration: 2500 });
        }
      },
      error: (err) => {
        console.error(err);
        this.messages.push({ role: 'assistant', text: 'Error generating answer.', ts: new Date() });
        this.answering = false;
        this.snack.open('Error generating answer.', 'Dismiss', { duration: 3000 });
      }
    });
  }

  getModels() {
    const params: any = {};
    if (this.geminiKey) params.gemini_api_key = this.geminiKey;
    this.api.models(this.geminiKey).subscribe(console.log);
  }

  validateKey() {
    if (!this.geminiKey) {
      this.keyStatus = 'not_configured';
      this.snack.open('Please enter an API key to validate.', 'Dismiss', { duration: 2500 });
      return;
    }
    this.keyStatus = 'checking';
    this.api.models(this.geminiKey).subscribe({
      next: (res: any) => {
        this.embeddingModel = res.embedding_model || undefined;
        this.generationModel = res.generation_model || undefined;
        this.availableModels = res.available_models || [];
        if (this.generationModel || this.embeddingModel) {
          this.keyStatus = 'valid';
          this.snack.open('Connected to Gemini.', 'OK', { duration: 2000 });
          this.apiCollapsed = true;
        } else {
          this.keyStatus = 'invalid';
          this.snack.open('Key seems invalid or lacks access to models.', 'Dismiss', { duration: 3000 });
        }
      },
      error: (err) => {
        console.error(err);
        this.keyStatus = 'invalid';
        this.snack.open('Failed to validate the key.', 'Dismiss', { duration: 3000 });
      }
    });
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.dragOver = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.dragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragOver = false;
    const file = event.dataTransfer?.files && event.dataTransfer.files[0];
    if (!file) return;
    const inputEvent = { target: { files: [file] } } as any;
    this.uploadFile(inputEvent);
  }

  clearFile() {
    this.uploadedFile = undefined;
    this.uploadProgress = 0;
    // Keep sessionId so the user can continue Q&A or re-upload into the same session
    this.uploadCollapsed = false;
  }

  scrollToMain() {
    document.getElementById('main-cards')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  renderMarkdown(md: string): SafeHtml {
    // Very light markdown: **bold**, _italic_, `code`, bullet lists, line breaks
    let html = md
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    html = html
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
    // Lists: lines starting with - or *
    const lines = html.split(/\r?\n/);
    const out: string[] = [];
    let inList = false;
    for (const line of lines) {
      if (/^\s*[-*]\s+/.test(line)) {
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push('<li>' + line.replace(/^\s*[-*]\s+/, '') + '</li>');
      } else {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push('<p>' + line + '</p>');
      }
    }
    if (inList) out.push('</ul>');
    return this.sanitizer.bypassSecurityTrustHtml(out.join('\n'));
  }

  formatTime(d?: Date): string {
    if (!d) return '';
    const hh = d.getHours().toString().padStart(2, '0');
    const mm = d.getMinutes().toString().padStart(2, '0');
    return `${hh}:${mm}`;
  }
}
