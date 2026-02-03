# Jira Integration Setup Guide

This guide explains how to configure the Jira integration for exporting console errors and warnings to Jira tickets.

## Required Environment Variables

Add the following variables to your `.env` file in the `backend` directory:

```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=PROJ
JIRA_ISSUE_TYPE=Bug
```

## How to Get Each Value

### 1. JIRA_URL
This is your Jira instance URL. It typically looks like:
- `https://yourcompany.atlassian.net` (for Atlassian Cloud)
- `https://jira.yourcompany.com` (for self-hosted Jira)

**How to find it:**
- Look at the URL when you're logged into Jira in your browser
- It's the base URL before `/browse/` or any other path

### 2. JIRA_EMAIL
This is the email address of the Jira user account that will create the tickets.

**Requirements:**
- Must be a valid Jira user account
- The account must have permission to create issues in the target project
- Use the email address you use to log into Jira

### 3. JIRA_API_TOKEN
This is an API token used for authentication instead of a password.

**How to create it:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label (e.g., "TestFlow Integration")
4. Click "Create"
5. **Copy the token immediately** - you won't be able to see it again!
6. Paste it as the value for `JIRA_API_TOKEN` in your `.env` file

**Note:** For self-hosted Jira, you may need to use a different authentication method. Check your Jira administrator.

### 4. JIRA_PROJECT_KEY
This is the short key/identifier for the Jira project where tickets will be created.

**How to find it:**
1. Go to your Jira project
2. Look at the URL - it will be something like: `https://yourcompany.atlassian.net/browse/PROJ-123`
3. The part before the dash (e.g., `PROJ`) is your project key
4. Or check the project settings - the key is usually displayed there

**Examples:**
- `PROJ`
- `DEV`
- `TEST`
- `BUG`

### 5. JIRA_ISSUE_TYPE (Optional)
The type of issue to create in Jira. Defaults to `Bug` if not specified.

**Common values:**
- `Bug`
- `Task`
- `Story`
- `Issue`

**How to find valid issue types:**
1. Go to your Jira project
2. Click "Create" to create a new issue
3. Look at the dropdown for issue types
4. Use the exact name as it appears (case-sensitive)

## Example .env Configuration

```env
# Jira Configuration
JIRA_URL=https://mycompany.atlassian.net
JIRA_EMAIL=john.doe@mycompany.com
JIRA_API_TOKEN=ATATT3xFfGF0k7...your-token-here
JIRA_PROJECT_KEY=DEV
JIRA_ISSUE_TYPE=Bug
```

## Testing Your Configuration

After setting up the environment variables:

1. Restart your Django backend server
2. Run a test that generates console errors or warnings
3. Go to the report view
4. Click "Export" → "Export to Jira"
5. If successful, you'll see a toast notification with the created ticket keys
6. Click "View Tickets" to open the tickets in Jira

## Troubleshooting

### Error: "Missing required Jira configuration"
- Make sure all required variables are set in your `.env` file
- Restart the Django server after adding/changing environment variables
- Check that there are no extra spaces or quotes around the values

### Error: "Failed to initialize Jira client"
- Verify your `JIRA_URL` is correct and accessible
- Check that `JIRA_EMAIL` and `JIRA_API_TOKEN` are correct
- Make sure the API token hasn't expired (they don't expire, but you might have deleted it)

### Error: "Project not found" or "Permission denied"
- Verify `JIRA_PROJECT_KEY` is correct (case-sensitive)
- Ensure the user account has permission to create issues in that project
- Check that `JIRA_ISSUE_TYPE` is a valid issue type for that project

### Error: "Jira library not installed"
- Run: `pip install jira`
- Or: `pip install -r requirements.txt` (which includes jira==3.7.1)

## Security Notes

- **Never commit your `.env` file to version control**
- Keep your API token secure
- If your token is compromised, revoke it immediately and create a new one
- Use environment-specific tokens (different tokens for dev/staging/production)

## Support

If you continue to have issues:
1. Check the Django server logs for detailed error messages
2. Verify your Jira account has the necessary permissions
3. Test the Jira API connection manually using curl or Postman
4. Contact your Jira administrator if you need help with permissions or project configuration

