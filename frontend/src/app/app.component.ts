import { Component, OnInit } from '@angular/core';
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
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatListModule } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDialogModule } from '@angular/material/dialog';
import { HttpEventType } from '@angular/common/http';
import { ApiService, Session, Conversation, Document } from './api.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

type ViewMode = 'dashboard' | 'session' | 'settings';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: any[];
  llm_used?: string;
  created_at?: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatInputModule, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatCardModule, MatChipsModule, MatSnackBarModule,
    MatTooltipModule, MatProgressSpinnerModule, MatSelectModule, MatFormFieldModule,
    MatListModule, MatDividerModule, MatMenuModule, MatBadgeModule, MatDialogModule
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'FINQUEST AI';
  
  // View state
  viewMode: ViewMode = 'dashboard';
  
  // Sessions
  sessions: Session[] = [];
  currentSession: Session | null = null;
  loadingSessions = false;
  
  // New session creation
  newSessionName = '';
  newSessionLLM: 'gemini' | 'chatgpt' = 'gemini';
  creatingSession = false;
  
  // Document upload
  uploadProgress = 0;
  uploading = false;
  currentDocument: string = '';
  documents: Document[] = [];
  
  // Chat
  messages: ChatMessage[] = [];
  question = '';
  answering = false;
  
  // Sample questions (suggestions)
  sampleQuestions = [
    "What is this document about?",
    "Summarize the main points",
    "What are the key findings?",
    "List all dates mentioned",
    "Who are the parties involved?",
    "What are the recommendations?"
  ];
  
  // Use a sample question
  useSampleQuestion(question: string) {
    this.question = question;
    // Optionally auto-submit
    // this.ask();
  }
  
  // Settings
  geminiApiKey = '';
  chatgptApiKey = '';
  groqApiKey = '';
  savingSettings = false;
  
  // UI state
  dragOver = false;
  sidebarOpen = true;

  constructor(
    private api: ApiService,
    private snack: MatSnackBar,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit() {
    this.loadSessions();
    this.loadSettings();
  }

  // ========== Session Management ==========

  loadSessions() {
    this.loadingSessions = true;
    this.api.listSessions().subscribe({
      next: (sessions) => {
        this.sessions = sessions;
        this.loadingSessions = false;
      },
      error: (err) => {
        console.error('Failed to load sessions:', err);
        this.snack.open('Failed to load sessions', 'Dismiss', { duration: 3000 });
        this.loadingSessions = false;
      }
    });
  }

  createSession() {
    if (!this.newSessionName.trim()) {
      this.snack.open('Please enter a session name', 'Dismiss', { duration: 2000 });
      return;
    }

    this.creatingSession = true;
    this.api.createSession(this.newSessionName, this.newSessionLLM).subscribe({
      next: (session) => {
        this.sessions.unshift(session);
        this.newSessionName = '';
        this.creatingSession = false;
        this.snack.open(`Session "${session.session_name}" created`, 'OK', { duration: 2000 });
        this.openSession(session);
      },
      error: (err) => {
        console.error('Failed to create session:', err);
        this.snack.open('Failed to create session', 'Dismiss', { duration: 3000 });
        this.creatingSession = false;
      }
    });
  }

  openSession(session: Session) {
    this.currentSession = session;
    this.viewMode = 'session';
    this.loadSessionData();
  }

  loadSessionData() {
    if (!this.currentSession) return;

    // Load documents
    this.api.listDocuments(this.currentSession.session_id).subscribe({
      next: (docs) => {
        this.documents = docs;
      },
      error: (err) => {
        console.error('Failed to load documents:', err);
      }
    });

    // Load conversations
    this.api.getConversations(this.currentSession.session_id).subscribe({
      next: (conversations) => {
        this.messages = [];
        for (const conv of conversations) {
          this.messages.push({
            role: 'user',
            text: conv.query,
            created_at: conv.created_at
          });
          this.messages.push({
            role: 'assistant',
            text: conv.response,
            sources: conv.sources,
            llm_used: conv.llm_used,
            created_at: conv.created_at
          });
        }
      },
      error: (err) => {
        console.error('Failed to load conversations:', err);
      }
    });
  }

  deleteSession(session: Session, event: Event) {
    event.stopPropagation();
    
    if (!confirm(`Delete session "${session.session_name}"? This will delete all documents and conversations.`)) {
      return;
    }

    this.api.deleteSession(session.session_id).subscribe({
      next: () => {
        this.sessions = this.sessions.filter(s => s.session_id !== session.session_id);
        if (this.currentSession?.session_id === session.session_id) {
          this.backToDashboard();
        }
        this.snack.open('Session deleted', 'OK', { duration: 2000 });
      },
      error: (err) => {
        console.error('Failed to delete session:', err);
        this.snack.open('Failed to delete session', 'Dismiss', { duration: 3000 });
      }
    });
  }

  backToDashboard() {
    this.viewMode = 'dashboard';
    this.currentSession = null;
    this.messages = [];
    this.documents = [];
    this.question = '';
    this.loadSessions();
  }

  // ========== Document Upload ==========

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (!file) return;
    this.uploadFile(file);
  }

  uploadFile(file: File) {
    if (!this.currentSession) {
      this.snack.open('No session selected', 'Dismiss', { duration: 2000 });
      return;
    }

    const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.markdown'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedTypes.includes(ext)) {
      this.snack.open(`Only ${allowedTypes.join(', ')} files are supported`, 'Dismiss', { duration: 3000 });
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      this.snack.open('File too large. Max 20MB allowed.', 'Dismiss', { duration: 3000 });
      return;
    }

    this.uploading = true;
    this.uploadProgress = 0;
    this.currentDocument = file.name;

    this.api.uploadDocument(this.currentSession.session_id, file).subscribe({
      next: (event: any) => {
        if (event.type === HttpEventType.UploadProgress) {
          this.uploadProgress = Math.round(100 * event.loaded / (event.total || event.loaded));
        } else if (event.type === HttpEventType.Response) {
          const data = event.body;
          this.uploading = false;
          this.uploadProgress = 0;
          this.currentDocument = '';
          this.snack.open(`Document "${file.name}" uploaded successfully`, 'OK', { duration: 2500 });
          this.loadSessionData();
        }
      },
      error: (err) => {
        console.error('Upload failed:', err);
        this.uploading = false;
        this.uploadProgress = 0;
        this.currentDocument = '';
        this.snack.open('Upload failed. Please try again.', 'Dismiss', { duration: 3000 });
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
    if (file) {
      this.uploadFile(file);
    }
  }

  // ========== Chat / Query ==========

  ask() {
    if (!this.currentSession) {
      this.snack.open('No session selected', 'Dismiss', { duration: 2000 });
      return;
    }

    const q = this.question.trim();
    if (!q) return;

    this.messages.push({ 
      role: 'user', 
      text: q,
      created_at: new Date().toISOString()
    });
    this.answering = true;

    this.api.query(this.currentSession.session_id, q).subscribe({
      next: (data) => {
        this.messages.push({
          role: 'assistant',
          text: data.answer,
          sources: data.sources,
          llm_used: data.llm_used,
          created_at: new Date().toISOString()
        });
        this.question = '';
        this.answering = false;
        if (data.used_fallback) {
          this.snack.open(`Answer from ${data.llm_used} (fallback)`, 'Info', { duration: 2500 });
        }
      },
      error: (err) => {
        console.error('Query failed:', err);
        this.messages.push({
          role: 'assistant',
          text: 'Error generating answer. Please try again.',
          created_at: new Date().toISOString()
        });
        this.answering = false;
        this.snack.open('Error generating answer', 'Dismiss', { duration: 3000 });
      }
    });
  }

  // ========== Settings ==========

  openSettings() {
    this.viewMode = 'settings';
  }

  loadSettings() {
    this.api.getAllConfig().subscribe({
      next: (config) => {
        if (config.gemini_api_key) {
          this.geminiApiKey = config.gemini_api_key;
        }
        if (config.chatgpt_api_key) {
          this.chatgptApiKey = config.chatgpt_api_key;
        }
        if (config.groq_api_key) {
          this.groqApiKey = config.groq_api_key;
        }
      },
      error: (err) => {
        console.error('Failed to load settings:', err);
      }
    });
  }

  saveSettings() {
    this.savingSettings = true;
    
    const saves = [];
    if (this.geminiApiKey.trim()) {
      saves.push(this.api.setConfig('gemini_api_key', this.geminiApiKey.trim()));
    }
    if (this.chatgptApiKey.trim()) {
      saves.push(this.api.setConfig('chatgpt_api_key', this.chatgptApiKey.trim()));
    }
    if (this.groqApiKey.trim()) {
      saves.push(this.api.setConfig('groq_api_key', this.groqApiKey.trim()));
    }

    if (saves.length === 0) {
      this.snack.open('No API keys to save', 'Dismiss', { duration: 2000 });
      this.savingSettings = false;
      return;
    }

    // Use Promise.all to wait for all saves
    Promise.all(saves.map(obs => obs.toPromise())).then(
      () => {
        this.savingSettings = false;
        this.snack.open('Settings saved successfully', 'OK', { duration: 2000 });
      },
      (err) => {
        console.error('Failed to save settings:', err);
        this.savingSettings = false;
        this.snack.open('Failed to save settings', 'Dismiss', { duration: 3000 });
      }
    );
  }

  // ========== Helpers ==========

  formatDate(dateStr?: string): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    
    return date.toLocaleDateString();
  }

  formatTime(dateStr?: string): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `${hh}:${mm}`;
  }

  renderMarkdown(md: string): SafeHtml {
    // Basic markdown rendering
    let html = md
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    html = html
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\[Source (\d+)\]/g, '<span class="source-tag">[Source $1]</span>');
    
    // Lists
    const lines = html.split(/\r?\n/);
    const out: string[] = [];
    let inList = false;
    
    for (const line of lines) {
      if (/^\s*[-*]\s+/.test(line)) {
        if (!inList) {
          out.push('<ul>');
          inList = true;
        }
        out.push('<li>' + line.replace(/^\s*[-*]\s+/, '') + '</li>');
      } else {
        if (inList) {
          out.push('</ul>');
          inList = false;
        }
        if (line.trim()) {
          out.push('<p>' + line + '</p>');
        }
      }
    }
    if (inList) out.push('</ul>');
    
    return this.sanitizer.bypassSecurityTrustHtml(out.join('\n'));
  }

  getLLMIcon(llm?: string): string {
    switch (llm) {
      case 'gemini': return 'auto_awesome';
      case 'chatgpt': return 'psychology';
      case 'local-llm': return 'computer';
      case 'heuristic': return 'search';
      case 'out-of-context': return 'warning';
      default: return 'smart_toy';
    }
  }

  getLLMColor(llm?: string): string {
    switch (llm) {
      case 'gemini': return '#4285f4';
      case 'chatgpt': return '#10a37f';
      case 'local-llm': return '#ff9800';
      case 'heuristic': return '#9e9e9e';
      case 'out-of-context': return '#f44336';
      default: return '#757575';
    }
  }
}
