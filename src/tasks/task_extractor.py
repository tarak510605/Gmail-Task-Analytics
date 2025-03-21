from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from auth.gmail_auth import GmailAuth
import re
from dateutil import parser
from dateutil.relativedelta import relativedelta
from functools import lru_cache

class TaskExtractor:
    def __init__(self):
        self.auth = GmailAuth()
        self.service = None
        self.task_categories = ['Work', 'Personal', 'Meeting', 'Follow-up', 'Review', 'Other']
        # Enhanced task keywords with more comprehensive patterns
        self.task_keywords = [
            # Action verbs
            'todo', 'task', 'action item', 'please', 'need to', 'should', 'must',
            'required', 'urgent', 'important', 'priority', 'asap', 'follow up',
            'review', 'update', 'prepare', 'send', 'complete', 'finish', 'submit',
            'deliver', 'schedule', 'organize', 'coordinate', 'implement', 'develop',
            'create', 'ensure', 'verify', 'check', 'investigate', 'resolve', 'handle',
            # Request indicators
            'can you', 'could you', 'would you', 'will you', 'please help',
            'requesting', 'request for', 'need your', 'looking for', 'seeking',
            # Action items
            'action required', 'action needed', 'next steps', 'deliverable',
            'assignment', 'to-do', 'todo item', 'work item', 'pending',
            # Responsibility indicators
            'responsible for', 'in charge of', 'take care of', 'handle this',
            'assigned to', 'your task', 'your responsibility',
            # Time-sensitive indicators
            'time sensitive', 'time-critical', 'urgent matter', 'immediate attention',
            'as soon as possible', 'right away', 'promptly', 'expedite'
        ]
        
        # Deadline-related patterns
        self.deadline_keywords = [
            'due by', 'deadline', 'by', 'until', 'due date', 'due on',
            'needs to be done', 'must be completed', 'complete by',
            'finish by', 'submit by', 'deliver by', 'required by',
            'expected by', 'no later than', 'before', 'prior to',
            'end of', 'eod', 'cob', 'close of business'
        ]
        
        # Date patterns for regex matching
        self.date_patterns = {
            'formal': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            'written': r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
                      r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
                      r'Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:[,]\s*\d{4})?',
            'relative': r'(?:next|this|coming)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|week|month)'
        }
        
        # Precompile regex patterns
        self.compiled_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.date_patterns.items()}

    def connect(self) -> bool:
        if self.auth.authenticate():
            self.service = self.auth.get_service()
            return True
        return False

    def extract_tasks(self, emails: List[Dict]) -> List[Dict]:
        tasks = []
        for email in emails:
            # Extract tasks from email subject and body with improved content analysis
            subject = email['subject']
            body = email['snippet']
            
            # Check subject line first (higher priority)
            subject_task = self._analyze_content(subject, is_subject=True)
            if subject_task:
                # Extract deadline from full email body for better accuracy
                deadline_info = self._extract_deadline(body)
                if deadline_info['date']:
                    subject_task['deadline'] = deadline_info['date']
                    subject_task['deadline_confidence'] = deadline_info['confidence']
                    subject_task['deadline_context'] = deadline_info['context']
                
                subject_task.update({
                    'from': email['from'],
                    'source': 'subject'
                })
                tasks.append(subject_task)
            
            # Then check email body
            body_task = self._analyze_content(body, is_subject=False)
            if body_task:
                # Use the same deadline info for body task if available
                if 'deadline' not in body_task and deadline_info['date']:
                    body_task['deadline'] = deadline_info['date']
                    body_task['deadline_confidence'] = deadline_info['confidence']
                    body_task['deadline_context'] = deadline_info['context']
                
                body_task.update({
                    'from': email['from'],
                    'source': 'body'
                })
                tasks.append(body_task)
        
        return tasks

    def _analyze_content(self, text: str, is_subject: bool = False) -> Optional[Dict]:
        """Enhanced content analysis for task detection."""
        text_lower = text.lower()
        
        # Initialize confidence score
        confidence_score = 0.0
        
        # Check for task keywords (weighted by position and source)
        for keyword in self.task_keywords:
            if keyword in text_lower:
                # Higher weight for subject line matches
                confidence_score += 0.3 if is_subject else 0.2
                # Higher weight for keywords at the start
                if text_lower.startswith(keyword):
                    confidence_score += 0.1
        
        # Check for action verbs at the beginning
        action_verbs = ['please', 'need', 'must', 'should', 'will', 'can']
        if any(text_lower.startswith(verb) for verb in action_verbs):
            confidence_score += 0.2
        
        # Check for question marks (potential requests)
        if '?' in text:
            confidence_score += 0.1
        
        # Check for deadline keywords
        deadline_info = self._extract_deadline(text)
        if deadline_info['date']:
            confidence_score += 0.3  # Increase confidence if deadline is found
        
        # Only create task if confidence threshold is met
        if confidence_score >= 0.3:
            return {
                'text': text,
                'priority': self._determine_priority(text, deadline_info),
                'category': self._determine_category(text),
                'deadline': deadline_info['date'] if isinstance(deadline_info['date'], str) else deadline_info['date'].isoformat() if deadline_info['date'] else '',
                'deadline_context': deadline_info['context'] if deadline_info['context'] else '',
                'confidence': confidence_score,
                'status': 'pending'
            }
        
        return None

    def _determine_priority(self, text: str, deadline_info: Dict = None) -> str:
        text_lower = text.lower()
        priority_score = 0.0
        
        # Check for urgency words
        urgency_words = [
            'urgent', 'asap', 'immediately', 'priority', 'important',
            'critical', 'crucial', 'essential', 'time-sensitive',
            'expedite', 'rush', 'pressing', 'high priority'
        ]
        
        # Calculate urgency score
        if any(word in text_lower for word in urgency_words):
            priority_score += 0.4
        
        # Check for time-sensitive phrases
        time_sensitive_phrases = [
            'as soon as', 'right away', 'urgent attention',
            'quick response', 'immediate action', 'time sensitive'
        ]
        if any(phrase in text_lower for phrase in time_sensitive_phrases):
            priority_score += 0.3
        
        # Check deadline proximity if available
        if deadline_info and deadline_info['date']:
            try:
                deadline_date = datetime.fromisoformat(deadline_info['date']) if isinstance(deadline_info['date'], str) else deadline_info['date']
                time_until_deadline = deadline_date - datetime.now()
                hours_until_deadline = time_until_deadline.total_seconds() / 3600
                
                if hours_until_deadline <= 24:  # Within 24 hours
                    priority_score += 0.5
                elif hours_until_deadline <= 72:  # Within 72 hours
                    priority_score += 0.3
                elif hours_until_deadline <= 168:  # Within a week
                    priority_score += 0.2
            except (ValueError, TypeError):
                # If date parsing fails, don't modify priority score
                pass
        
        # Consider deadline confidence
        if deadline_info and deadline_info['confidence'] > 0.7:
            priority_score += 0.2
        
        return 'high' if priority_score >= 0.4 else 'moderate'

    def _determine_category(self, text: str) -> str:
        # Simple keyword-based categorization
        keywords = {
            'Work': ['report', 'project', 'meeting', 'client', 'deadline'],
            'Personal': ['family', 'home', 'personal', 'appointment'],
            'Meeting': ['meet', 'call', 'conference', 'discuss'],
            'Follow-up': ['follow up', 'check', 'confirm', 'verify'],
            'Review': ['review', 'feedback', 'evaluate', 'assess']
        }
        
        text_lower = text.lower()
        for category, words in keywords.items():
            if any(word in text_lower for word in words):
                return category
        return 'Other'

    def prioritize_tasks(self, tasks: List[Dict], sort_by: str = 'priority', reverse: bool = True) -> List[Dict]:
        # Process tasks in batches for better performance
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            for task in batch:
                # Extract and analyze deadline only if not already present
                if 'deadline' not in task:
                    deadline_info = self._extract_deadline(task['text'])
                    if deadline_info['date']:
                        task['deadline'] = deadline_info['date'].isoformat()
                        task['deadline_confidence'] = deadline_info['confidence']
                        task['deadline_context'] = deadline_info['context']
                
                # Calculate priority if not already set
                if 'priority' not in task:
                    deadline_date = task.get('deadline')
                    task['priority'] = self._determine_priority(task['text'])

        # Use optimized sorting with key functions
        sort_keys = {
            'priority': lambda x: (x['priority'] == 'high', x.get('deadline', '')),
            'deadline': lambda x: (x.get('deadline', ''), x['priority'] == 'high'),
            'category': lambda x: (x['category'], x['priority'] == 'high'),
            'status': lambda x: (x['status'] == 'pending', x['priority'] == 'high')
        }

        return sorted(tasks, key=sort_keys.get(sort_by, sort_keys['priority']), reverse=reverse)

    def _extract_deadline(self, text: str) -> Dict:
        """Extract deadline information using enhanced pattern matching."""
        result = {
            'date': None,
            'confidence': 0.0,
            'context': ''
        }
        
        # Early return if no text
        if not text:
            return result
            
        dates = []
        text_lower = text.lower()
        
        # First check for explicit deadline phrases
        deadline_phrases = [
            'due by', 'deadline is', 'due date', 'needs to be done by',
            'must be completed by', 'required by', 'finish by', 'submit by',
            'no later than', 'by end of', 'by close of business'
        ]
        
        # Add microseconds to ensure unique timestamps
        base_time = datetime.now().replace(microsecond=0)
        
        # First check for explicit dates in the text
        for pattern_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                try:
                    date_str = match.group(0)
                    if pattern_type == 'relative':
                        date = self._parse_relative_date(date_str)
                    else:
                        # Enhanced date parsing with multiple formats
                        try:
                            # First try parsing with explicit formats
                            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%b %d %Y', '%B %d %Y']:
                                try:
                                    date = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            
                            # If explicit formats fail, try fuzzy parsing
                            if not date:
                                date = parser.parse(date_str, fuzzy=True, default=base_time)
                                
                            # If date is parsed as today but text suggests future, add one day
                            if date.date() == base_time.date() and any(word in text_lower for word in ['tomorrow', 'next']):
                                date += timedelta(days=1)
                        except (ValueError, TypeError):
                            continue
                    
                    # Validate and adjust date if needed
                    if date:
                        # If date is past, try to interpret as next occurrence
                        if date < base_time:
                            # For dates without year, assume next occurrence
                            if '%Y' not in date_str:
                                date = date.replace(year=base_time.year)
                                if date < base_time:
                                    date = date.replace(year=date.year + 1)
                        
                        # Add microseconds to ensure unique timestamps
                        date = date.replace(microsecond=len(dates))
                        dates.append((date, match.span()))
                except Exception as e:
                    continue
        
        # Check for relative time expressions if no explicit dates found
        if not dates:
            relative_time = self._check_relative_time(text_lower)
            if relative_time and relative_time > datetime.now():
                dates.append((relative_time, (0, 0)))
        
        if not dates:
            return result
        
        # Enhanced context analysis with deadline phrases
        best_date = None
        best_confidence = 0.0
        best_context = ''
        
        deadline_phrases = [
            'due by', 'deadline is', 'due date', 'needs to be done by',
            'must be completed by', 'required by', 'finish by', 'submit by',
            'no later than', 'by end of', 'by close of business',
            'by eod', 'by cob', 'by tomorrow', 'by next', 'due', 'deadline'
        ]
        
        for date, (start, end) in dates:
            # Get broader context
            context_start = max(0, text.rfind(' ', 0, start - 50))
            context_end = text.find(' ', end + 50)
            if context_end == -1:
                context_end = len(text)
            context = text[context_start:context_end].strip()
            
            # Calculate confidence score with improved weighting
            confidence = 0.0
            
            # Higher confidence for explicit deadline phrases
            for phrase in deadline_phrases:
                if phrase in context.lower():
                    confidence += 0.4
                    # Extra weight for phrases at the start
                    if context.lower().startswith(phrase):
                        confidence += 0.2
                    break
            
            # Higher confidence for dates closer to now
            days_until = (date - datetime.now()).days
            if 0 <= days_until <= 7:  # Within a week
                confidence += 0.4
            elif 7 < days_until <= 30:  # Within a month
                confidence += 0.3
            elif 30 < days_until <= 90:  # Within three months
                confidence += 0.2
            
            # Check for urgency indicators
            urgency_markers = ['urgent', 'asap', 'important', 'critical', 'immediate', 'priority']
            for marker in urgency_markers:
                if marker in context.lower():
                    confidence += 0.3
                    break
            
            # Higher confidence for dates in subject line
            if 'subject:' in text_lower[:start].lower():
                confidence += 0.3
            
            if confidence > best_confidence:
                best_date = date
                best_confidence = confidence
                best_context = context
        
        if best_date:
            result['date'] = best_date.isoformat()
            result['confidence'] = min(best_confidence, 1.0)
            result['context'] = best_context
        
        return result
    
    def _check_relative_time(self, text: str) -> Optional[datetime]:
        """Check for relative time expressions with enhanced patterns."""
        now = datetime.now()
        
        # Enhanced relative time patterns
        patterns = {
            r'today|by today|due today': timedelta(days=0),
            r'tomorrow|by tomorrow|due tomorrow': timedelta(days=1),
            r'next week|by next week|due next week': timedelta(weeks=1),
            r'next month|by next month|due next month': relativedelta(months=1),
            r'end of day|eod|by eod|close of business|cob|by cob': timedelta(days=1, hours=-now.hour),
            r'end of week|eow|by eow': timedelta(days=(4-now.weekday()) if now.weekday() <= 4 else (7-now.weekday()+5)),
            r'end of month|eom|by eom': relativedelta(months=1, day=1) - relativedelta(days=1),
            r'in \d+ days?': lambda m: timedelta(days=int(re.search(r'\d+', m).group())),
            r'in \d+ weeks?': lambda m: timedelta(weeks=int(re.search(r'\d+', m).group())),
            r'in \d+ months?': lambda m: relativedelta(months=int(re.search(r'\d+', m).group())),
            r'next (?:mon|tue|wed|thu|fri|sat|sun)(?:day)?': lambda m: self._get_next_weekday(m),
            r'this (?:mon|tue|wed|thu|fri|sat|sun)(?:day)?': lambda m: self._get_this_weekday(m)
        }
        
        for pattern, delta in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if callable(delta):
                    return now + delta(match.group())
                return now + delta
        
        return None

    def _get_next_weekday(self, match_text: str) -> timedelta:
        """Get the next occurrence of a weekday."""
        weekdays = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        now = datetime.now()
        day_text = match_text.lower()[:3]
        target_day = weekdays[day_text]
        days_ahead = target_day - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return timedelta(days=days_ahead)

    def _get_this_weekday(self, match_text: str) -> timedelta:
        """Get this week's occurrence of a weekday."""
        weekdays = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        now = datetime.now()
        day_text = match_text.lower()[:3]
        target_day = weekdays[day_text]
        days_ahead = target_day - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return timedelta(days=days_ahead)
    
    def _parse_relative_date(self, text: str) -> datetime:
        """Parse relative date expressions."""
        now = datetime.now()
        text = text.lower()
        
        if 'next' in text or 'coming' in text:
            if 'week' in text:
                return now + timedelta(weeks=1)
            elif 'month' in text:
                return now + relativedelta(months=1)
            else:
                # Handle next weekday
                weekdays = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2,
                    'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
                }
                for day, day_num in weekdays.items():
                    if day in text:
                        days_ahead = day_num - now.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return now + timedelta(days=days_ahead)
        
        return now
    
    def filter_tasks(self, tasks: List[Dict], filters: Dict) -> List[Dict]:
        filtered_tasks = tasks
        
        if 'priority' in filters:
            filtered_tasks = [t for t in filtered_tasks if t['priority'] == filters['priority']]
        
        if 'category' in filters:
            filtered_tasks = [t for t in filtered_tasks if t['category'] == filters['category']]
        
        if 'status' in filters:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == filters['status']]
        
        if 'completed' in filters:
            filtered_tasks = [t for t in filtered_tasks if t['completed'] == filters['completed']]
        
        return filtered_tasks

    def update_task_status(self, task: Dict, status: str) -> None:
        """Update the status of a task and set completion date if needed."""
        task['status'] = status.lower()
        task['completed'] = status.lower() == 'completed'
        if task['completed']:
            task['completion_date'] = datetime.now().isoformat()
        task['last_modified'] = datetime.now().isoformat()