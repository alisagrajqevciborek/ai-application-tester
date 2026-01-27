"""
Issue grouping utilities to consolidate similar issues.
"""
from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


def group_similar_issues(issues: List[Dict]) -> List[Dict]:
    """
    Group similar issues together to reduce repetition.
    
    Groups issues by:
    - Console errors (CORS, font loading, etc.)
    - Network failures (404s, 500s, etc.)
    - Missing elements (alt text, meta tags, etc.)
    - Accessibility issues (ARIA, headings, etc.)
    
    Returns grouped issues with frequency counts and representative screenshots.
    """
    if not issues:
        return []
    
    # Define grouping patterns
    groups = {}
    
    for issue in issues:
        title = issue.get('title', '').lower()
        description = issue.get('description', '').lower()
        severity = issue.get('severity', 'minor')
        location = issue.get('location', '')
        
        # Determine group key
        group_key = None
        group_type = None
        
        # Console error patterns
        if 'console error' in title or 'console error' in description:
            if 'cors' in description or 'cross-origin' in description:
                group_key = 'cors_errors'
                group_type = 'CORS Policy Errors'
            elif 'font' in description or 'font' in title:
                group_key = 'font_loading_errors'
                group_type = 'Font Loading Errors'
            elif 'network' in description or 'failed to load' in description:
                group_key = 'network_console_errors'
                group_type = 'Network Console Errors'
            else:
                group_key = 'console_errors'
                group_type = 'Console Errors'
        
        # Network failure patterns
        elif 'network' in title or 'failed' in title or '404' in description or '500' in description:
            status_match = re.search(r'(\d{3})', description)
            if status_match:
                status = status_match.group(1)
                if status.startswith('4'):
                    group_key = f'network_4xx'
                    group_type = f'Client Errors ({status})'
                elif status.startswith('5'):
                    group_key = f'network_5xx'
                    group_type = f'Server Errors ({status})'
            else:
                group_key = 'network_failures'
                group_type = 'Network Failures'
        
        # Missing elements patterns
        elif 'missing' in title or 'not found' in title:
            if 'alt' in description or 'alt text' in title:
                group_key = 'missing_alt_text'
                group_type = 'Missing Alt Text'
            elif 'meta' in description or 'meta' in title:
                group_key = 'missing_meta_tags'
                group_type = 'Missing Meta Tags'
            else:
                group_key = 'missing_elements'
                group_type = 'Missing Elements'
        
        # Accessibility patterns
        elif 'accessibility' in title or 'aria' in description or 'wcag' in description:
            if 'heading' in description:
                group_key = 'heading_issues'
                group_type = 'Heading Structure Issues'
            elif 'aria' in description:
                group_key = 'aria_issues'
                group_type = 'ARIA Label Issues'
            else:
                group_key = 'accessibility_issues'
                group_type = 'Accessibility Issues'
        
        # Performance patterns
        elif 'slow' in title or 'performance' in title or 'load time' in description:
            group_key = 'performance_issues'
            group_type = 'Performance Issues'
        
        # If no pattern matches, use individual issue
        if not group_key:
            group_key = f"individual_{len(groups)}"
            group_type = issue.get('title', 'Issue')
        
        # Add to group
        if group_key not in groups:
            groups[group_key] = {
                'type': group_type,
                'issues': [],
                'severity': severity,
                'locations': set(),
                'screenshots': []
            }
        
        groups[group_key]['issues'].append(issue)
        groups[group_key]['locations'].add(location)
        
        # Collect screenshots (up to 3 per group)
        if issue.get('element_screenshot') and len(groups[group_key]['screenshots']) < 3:
            groups[group_key]['screenshots'].append(issue['element_screenshot'])
        
        # Update severity to highest in group
        severity_order = {'critical': 3, 'major': 2, 'minor': 1}
        if severity_order.get(severity, 0) > severity_order.get(groups[group_key]['severity'], 0):
            groups[group_key]['severity'] = severity
    
    # Convert groups to grouped issues
    grouped_issues = []
    for group_key, group_data in groups.items():
        if len(group_data['issues']) > 1:
            # Create grouped issue
            count = len(group_data['issues'])
            locations = list(group_data['locations'])
            
            # Create description with details
            description = f"This issue occurred {count} time(s) on the following page(s): {', '.join(locations[:3])}"
            if len(locations) > 3:
                description += f" and {len(locations) - 3} more"
            
            # Add example issue details
            example_issue = group_data['issues'][0]
            description += f"\n\nExample: {example_issue.get('description', '')[:200]}"
            
            grouped_issue = {
                'severity': group_data['severity'],
                'title': f"{group_data['type']} ({count} occurrences)",
                'description': description,
                'location': ', '.join(locations[:2]) if locations else 'Multiple locations',
                'element_screenshot': group_data['screenshots'][0] if group_data['screenshots'] else None,
                'frequency': count,
                'affected_locations': locations,
                'all_screenshots': group_data['screenshots'],
                'is_grouped': True
            }
            grouped_issues.append(grouped_issue)
        else:
            # Single issue, keep as is
            grouped_issues.append(group_data['issues'][0])
    
    return grouped_issues
