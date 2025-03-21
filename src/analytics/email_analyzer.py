import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict
from auth.gmail_auth import GmailAuth
from functools import lru_cache
import pickle
import os
import base64

class EmailAnalyzer:
    def __init__(self):
        self.auth = GmailAuth()
        self.service = None
        self.cache_file = 'email_cache.pkl'
        self.batch_size = 100  # Process emails in batches of 100
        self.email_cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.email_cache, f)

    def connect(self) -> bool:
        if self.auth.authenticate():
            self.service = self.auth.get_service()
            return True
        return False

    def fetch_emails(self, months_back: int = 2, force_refresh: bool = False) -> List[Dict]:
        if not self.service:
            return []

        cache_key = f'emails_{months_back}'
        if not force_refresh and cache_key in self.email_cache:
            # Check if cache is from today
            now = datetime.now()
            if now.date() > datetime.fromtimestamp(os.path.getmtime(self.cache_file)).date():
                force_refresh = True

        if force_refresh or cache_key not in self.email_cache:
            date_from = (datetime.now() - pd.Timedelta(days=30*months_back))
            # Use RFC3339 format for more precise date filtering
            date_str = date_from.strftime('%Y-%m-%d')
            query = f'after:{date_str}'

            try:
                results = self.service.users().messages().list(
                    userId='me', q=query).execute()
                messages = results.get('messages', [])
                
                # Process emails in batches
                all_emails = []
                for i in range(0, len(messages), self.batch_size):
                    batch = messages[i:i + self.batch_size]
                    batch_emails = [self._get_email_data(msg['id']) for msg in batch]
                    all_emails.extend(batch_emails)

                # Cache the results
                self.email_cache[cache_key] = all_emails
                self._save_cache()
                
                return all_emails
            except Exception as e:
                print(f'Error fetching emails: {e}')
                return []
        
        return self.email_cache[cache_key]

    @lru_cache(maxsize=1000)
    def _get_email_data(self, msg_id: str) -> Dict:
        email = self.service.users().messages().get(
            userId='me', id=msg_id, format='full').execute()
        headers = email['payload']['headers']
        
        # Get email body content
        body = ''
        if 'parts' in email['payload']:
            for part in email['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in email['payload'] and 'data' in email['payload']['body']:
            body = base64.urlsafe_b64decode(email['payload']['body']['data']).decode('utf-8')
        
        return {
            'id': email['id'],
            'date': next(h['value'] for h in headers if h['name'] == 'Date'),
            'from': next(h['value'] for h in headers if h['name'] == 'From'),
            'subject': next(h['value'] for h in headers if h['name'] == 'Subject'),
            'snippet': email['snippet'],
            'body': body
        }

    def analyze_response_times(self, emails: List[Dict]) -> Dict:
        response_times = []
        email_threads = {}

        for email in emails:
            subject = email['subject']
            if 'Re:' in subject:
                base_subject = subject.replace('Re:', '').strip()
                if base_subject in email_threads:
                    email_threads[base_subject].append({
                        'date': datetime.strptime(email['date'], '%a, %d %b %Y %H:%M:%S %z'),
                        'from': email['from']
                    })

        for thread in email_threads.values():
            if len(thread) > 1:
                thread.sort(key=lambda x: x['date'])
                for i in range(1, len(thread)):
                    response_time = (thread[i]['date'] - thread[i-1]['date']).total_seconds() / 3600
                    response_times.append(response_time)

        if not response_times:
            return {'average': 0, 'min': 0, 'max': 0}

        return {
            'average': sum(response_times) / len(response_times),
            'min': min(response_times),
            'max': max(response_times)
        }

    def analyze_communication_patterns(self, emails: List[Dict]) -> Dict:
        patterns = {
            'peak_hours': {},
            'frequent_contacts': {},
            'daily_volume': {}
        }

        for email in emails:
            try:
                date = datetime.strptime(email['date'], '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                try:
                    date = datetime.strptime(email['date'], '%d %b %Y %H:%M:%S %z')
                except ValueError:
                    continue

            hour = date.hour
            patterns['peak_hours'][hour] = patterns['peak_hours'].get(hour, 0) + 1
            sender = email['from']
            patterns['frequent_contacts'][sender] = patterns['frequent_contacts'].get(sender, 0) + 1
            day = date.strftime('%Y-%m-%d')
            patterns['daily_volume'][day] = patterns['daily_volume'].get(day, 0) + 1

        patterns['peak_hours'] = dict(sorted(patterns['peak_hours'].items(), 
                                            key=lambda x: x[1], reverse=True)[:5])
        patterns['frequent_contacts'] = dict(sorted(patterns['frequent_contacts'].items(), 
                                                  key=lambda x: x[1], reverse=True)[:10])
        patterns['daily_volume'] = dict(sorted(patterns['daily_volume'].items()))

        return patterns

    def generate_email_network(self, emails: List[Dict]) -> go.Figure:
        G = nx.DiGraph()
        
        for email in emails:
            sender = email['from']
            G.add_node(sender, type='sender')
            
        pos = nx.spring_layout(G)
        
        edge_trace = go.Scatter(
            x=[], y=[], line=dict(width=0.5, color='#888'),
            hoverinfo='none', mode='lines')

        node_trace = go.Scatter(
            x=[], y=[], text=[], mode='markers+text',
            hoverinfo='text', textposition='bottom center',
            marker=dict(size=10, line_width=2))

        for node in G.nodes():
            x, y = pos[node]
            node_trace['x'] += tuple([x])
            node_trace['y'] += tuple([y])
            node_trace['text'] += tuple([node])

        fig = go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                        title='Email Communication Network',
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40)))
        
        return fig