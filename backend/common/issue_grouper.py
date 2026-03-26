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
        
        # Collect screenshots (up to 3 per group). Prefer most specific evidence,
        # but fall back to per-issue reference/context screenshots for non-element issues.
        if len(groups[group_key]['screenshots']) < 3:
            candidate = (
                issue.get('element_screenshot')
                or issue.get('annotated_screenshot')
                or issue.get('reference_screenshot')
                or issue.get('context_screenshot')
                or issue.get('after_screenshot')
                or issue.get('before_screenshot')
            )
            if candidate:
                groups[group_key]['screenshots'].append(candidate)
        
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
            
            # Extract rich context from all issues in the group
            resource_urls = []
            resource_types = []
            error_types = []
            error_messages = []
            
            for issue in group_data['issues']:
                desc = issue.get('description', '')
                title = issue.get('title', '')
                
                # Extract URLs from descriptions
                url_pattern = r'https?://[^\s\)]+'
                urls = re.findall(url_pattern, desc + ' ' + title)
                resource_urls.extend(urls[:1])  # One URL per issue
                
                # Determine resource type from URL or description
                url_text = (desc + ' ' + title).lower()
                if any(ext in url_text for ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
                    resource_types.append('font')
                elif any(ext in url_text for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                    resource_types.append('image')
                elif any(ext in url_text for ext in ['.js', '.mjs']):
                    resource_types.append('script')
                elif any(ext in url_text for ext in ['.css']):
                    resource_types.append('stylesheet')
                else:
                    resource_types.append('resource')
                
                # Extract error type
                if 'cors' in desc.lower() or 'cross-origin' in desc.lower():
                    error_types.append('CORS policy violation')
                elif '404' in desc or 'not found' in desc.lower():
                    error_types.append('File not found (404)')
                elif '500' in desc or 'server error' in desc.lower():
                    error_types.append('Server error (500)')
                elif 'failed to load' in desc.lower() or 'err_failed' in desc.lower():
                    error_types.append('Network failure')
                else:
                    error_types.append('Loading error')
                
                # Extract error message
                if 'console error:' in desc.lower():
                    error_msg = desc.split('console error:')[-1].strip()[:100]
                    if error_msg:
                        error_messages.append(error_msg)
            
            # Build user-friendly description with context for AI
            # This description will be completely rewritten by AI, but provides context
            unique_resource_types = list(set(resource_types))
            unique_error_types = list(set(error_types))
            
            # Create a simple, context-rich description for AI to work with
            description = f"Issue: {group_data['type']}\n\n"
            
            # What failed - in simple terms
            if unique_resource_types:
                type_str = ' and '.join(unique_resource_types)
                if count == 1:
                    description += f"One {type_str} file failed to load.\n"
                else:
                    description += f"{count} {type_str} files failed to load.\n"
            
            # Which files
            if resource_urls:
                unique_urls = list(dict.fromkeys(resource_urls))[:3]
                filenames = [url.split('/')[-1] for url in unique_urls]
                if len(filenames) == 1:
                    description += f"File: {filenames[0]}\n"
                elif len(filenames) <= 3:
                    description += f"Files: {', '.join(filenames)}\n"
                else:
                    description += f"Files include: {', '.join(filenames[:2])} and {len(filenames) - 2} more\n"
            
            # Error reason
            if unique_error_types:
                description += f"Reason: {unique_error_types[0]}\n"
            
            # Note: downstream pipeline may rewrite/enhance this description for end users.
            
            # Store additional context for AI
            grouped_issue = {
                'severity': group_data['severity'],
                'title': f"{group_data['type']} ({count} occurrences)",
                'description': description,
                'location': ', '.join(locations[:2]) if locations else 'Multiple locations',
                # Representative screenshot for the group (UI can also use all_screenshots)
                'element_screenshot': group_data['screenshots'][0] if group_data['screenshots'] else None,
                'reference_screenshot': group_data['screenshots'][0] if group_data['screenshots'] else None,
                'frequency': count,
                'affected_locations': locations,
                'all_screenshots': group_data['screenshots'],
                'is_grouped': True,
                # Additional context for AI
                'resource_types': unique_resource_types,
                'resource_urls': list(dict.fromkeys(resource_urls))[:5],
                'error_types': unique_error_types,
                'group_type': group_data['type']
            }
            grouped_issues.append(grouped_issue)
        else:
            # Single issue, keep as is
            grouped_issues.append(group_data['issues'][0])
    
    return grouped_issues
