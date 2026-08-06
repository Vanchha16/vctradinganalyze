# Authentication & RBAC

Version: 1.0

---

# 1. Objective

The Authentication & Authorization system secures the platform by verifying user identities and controlling access to platform resources.

The system must be:

- Secure
- Scalable
- Stateless
- API-first
- Compatible with Web and Mobile

---

# 2. Authentication Methods

Supported

✓ Email & Password

✓ Google OAuth

Future

Apple Login

GitHub Login

Microsoft Login

---

# 3. Registration Flow

**Superseded as of Phase 8E (docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md §9,
ADR-119).** The self-service flow originally described below (register →
verify email → activate → login) is no longer reachable - `POST
/auth/register` returns `403 registration_disabled` by default
(`settings.allow_public_registration=False`). Accounts are admin-provisioned
only:

- The platform's first account is created once via `backend/scripts/
  create_admin.py` (operator-run, ADR-123) - always `role=SUPER_ADMIN`,
  `must_change_password=False`, `created_by_admin_id=None`.
- Every account after that is created by an existing admin via
  `POST /admin/users` (`AdminUserService.create_user`, docs/59 §6.2) -
  `must_change_password=True`, `created_by_admin_id` set to the creating
  admin's id.

Both paths reuse the exact same underlying `UserService.register_user`
(password-policy validation, email/username uniqueness, Argon2id hashing) -
only *who* can reach that logic changed, not the logic itself. The original
flow below is preserved for historical context only - it does not describe
current behavior.

Original (historical, no longer reachable):

User

↓

Register

↓

Validate Input

↓

Create Account

↓

Send Verification Email

↓

Verify Email

↓

Activate Account

↓

Login

---

# 4. Login Flow

User

↓

Email + Password

↓

Validate Credentials

↓

Generate JWT

↓

Generate Refresh Token

↓

Store Session

↓

Return Tokens

---

# 5. JWT Tokens

Access Token

Purpose

API Authentication

Lifetime

15 minutes

---

Refresh Token

Purpose

Issue New Access Token

Lifetime

30 days

---

Tokens must be signed securely.

---

# 6. Session Management

Track

Session ID

Device

Browser

IP Address

Last Activity

Created Time

Expiration Time

Users can revoke individual sessions.

---

# 7. Password Policy

Minimum Length

12 characters

Require

Uppercase

Lowercase

Number

Special Character

Store

Argon2id hash

Never store plaintext passwords.

---

# 8. Email Verification

Required before accessing protected features.

Verification links expire after:

24 hours

Support:

Resend Verification Email

---

# 9. Password Reset

Flow

Forgot Password

↓

Generate Reset Token

↓

Email User

↓

Verify Token

↓

Set New Password

↓

Invalidate Old Sessions

---

# 10. Multi-Factor Authentication (Future)

Support

Authenticator Apps (TOTP)

Passkeys (WebAuthn)

Backup Codes

Trusted Devices

SMS is not recommended unless no stronger option is available.

---

# 11. Device Management

Users can view:

Current Device

Previous Devices

Location (Approximate)

Last Login

Allow

Logout Current Device

Logout Other Devices

Logout All Devices

---

# 12. User Roles

Guest

Registered User

Premium User

Moderator

Support

Administrator

Super Administrator

---

# 13. Role Permissions

Guest

View Public Pages

---

Registered User

Dashboard

Signals

Watchlist

AI Chat

---

Premium User

Advanced AI

Unlimited Watchlists

Premium Strategies

Reports

---

Moderator

Manage Reports

Review Feedback

Moderate Content

---

Support

View User Accounts

Assist Users

Cannot Access Passwords

---

Administrator

Manage Users

Manage Plans

Manage Content

Manage Signals

View Logs

---

Super Administrator

Full Platform Access

Infrastructure Configuration

System Settings

Emergency Controls

---

# 14. Permission Model

Permissions are granular.

Examples

users.read

users.update

signals.read

signals.create

signals.publish

news.manage

subscriptions.manage

admin.dashboard

system.settings

audit.view

---

# 15. Authorization

Every protected endpoint must verify:

Authentication

↓

Role

↓

Permission

↓

Resource Ownership

↓

Execute

---

# 16. Security Features

HTTPS Only

JWT Validation

CSRF Protection

Rate Limiting

Secure Cookies

Content Security Policy

Input Validation

SQL Injection Prevention

XSS Prevention

CORS Policy

---

# 17. Failed Login Protection

After multiple failed attempts:

Temporary Lock

CAPTCHA (Future)

Notify User

Log Event

**Built in Phase 9B (ADR-133).** This section originally specified no
threshold, duration, or reset rule - `settings.login_lockout_threshold`
(5) and `settings.login_lockout_duration_minutes` (15) are hand-picked
starting points, not calibrated (see ADR-133's Future Review). "Temporary
Lock" auto-expires on its own (no admin-unlock endpoint - see ADR-133's
Reason for why). "Notify User" is dropped, not built - it requires email
delivery, which Phase 9 dropped entirely (docs/60 §2). "Log Event" is
three distinguishable `AuditLog` actions: `login_failed`,
`login_failed_locked`, `account_locked`. "CAPTCHA (Future)" remains
deferred, unchanged.

---

# 18. Audit Logging

Log

Login

Logout

Password Reset

Permission Changes

Role Changes

Failed Logins

Session Revocation

Account Deletion

---

# 19. API Security

Require Authorization Header

Validate JWT Signature

Validate Expiration

Validate User Status

Reject Invalid Tokens

---

# 20. Output Example

{
    "user_id": "uuid",
    "role": "Premium User",
    "permissions": [
        "signals.read",
        "watchlist.manage",
        "ai.chat"
    ]
}

---

# 21. Testing

Validate

Registration

Login

JWT

Refresh Token

Role Enforcement

Permission Checks

Session Revocation

Coverage Goal

95%

---

# 22. Future Enhancements

Passkeys

Single Sign-On (SSO)

Enterprise Identity Providers

Risk-Based Authentication

Adaptive MFA

Security Dashboard