# Production Readiness Checklist

Use this checklist to ensure everything is ready before going live.

## Pre-Deployment

### Infrastructure
- [ ] Azure subscription verified and billing alerts set
- [ ] Resource group created: `auditapp-prod-rg`
- [ ] All Azure resources provisioned (run `infrastructure/deploy.sh`)
- [ ] Azure OpenAI resource accessible (existing cog-obghpsbi63abq)
- [ ] Database schema migrated (run alembic migrations)
- [ ] Storage containers created and accessible
- [ ] Redis cache configured and tested

### Application Configuration
- [ ] `.env.production` file created with all settings
- [ ] SQL database connection string updated
- [ ] Azure AI Search endpoint configured
- [ ] Blob storage connection string set
- [ ] Application Insights instrumentation key added
- [ ] Secret key generated (use `openssl rand -base64 32`)
- [ ] CORS origins updated with production domains

### Security
- [ ] All API keys moved to Azure Key Vault
- [ ] Managed identities enabled for Container Apps
- [ ] SQL firewall rules configured (allow Azure services)
- [ ] Blob storage private access only
- [ ] Redis SSL enabled
- [ ] No secrets committed to Git repository

### Code Readiness
- [ ] All tests passing locally
- [ ] Docker images build successfully
- [ ] No hardcoded credentials in code
- [ ] Logging configured (Application Insights)
- [ ] Error handling implemented
- [ ] Background processing tested

## Deployment

### Backend Deployment
- [ ] Docker image built for backend
- [ ] Image pushed to Azure Container Registry
- [ ] Container App created or updated
- [ ] Environment variables configured in Container App
- [ ] Health endpoint responding (GET /health)
- [ ] API documentation accessible (GET /docs)
- [ ] Background workers running

### Frontend Deployment
- [ ] Production build created (npm run build)
- [ ] Static files uploaded to Azure Static Web Apps
- [ ] API endpoint configured in frontend
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate applied
- [ ] CDN caching configured

### Database
- [ ] Database migrations applied
- [ ] Seed data loaded (if needed)
- [ ] Indexes created for performance
- [ ] Backup policy configured
- [ ] Connection pooling verified

## Post-Deployment Verification

### Functional Testing
- [ ] Create engagement via UI
- [ ] Upload single document (< 10MB)
- [ ] Upload multiple documents (10+ files)
- [ ] Document processing completes successfully
- [ ] View document status in UI
- [ ] Ask question and receive answer
- [ ] View Q&A history
- [ ] Delete document
- [ ] Delete engagement
- [ ] All API endpoints respond correctly

### Performance Testing
- [ ] Upload 50 documents simultaneously
- [ ] Verify processing completes within acceptable time
- [ ] Check CPU/memory usage under load
- [ ] Test with large files (50+ pages, 50MB+)
- [ ] Verify vector search performance (< 2 seconds)
- [ ] Check GPT-4 response time (< 5 seconds)

### Scale Testing (300-400 Documents)
- [ ] Upload 100 documents in batches
- [ ] Monitor queue depth
- [ ] Verify all documents process successfully
- [ ] Check Azure AI Search index size
- [ ] Test Q&A with 100+ documents loaded
- [ ] Monitor costs during heavy usage

### Monitoring & Alerts
- [ ] Application Insights data flowing
- [ ] Custom metrics being collected
- [ ] Error rate alert configured (> 5 errors/5min)
- [ ] Response time alert configured (> 3 seconds avg)
- [ ] Resource utilization alerts set
- [ ] Cost alert configured (> $100/day)
- [ ] Email notifications working

### Security Validation
- [ ] No API keys in logs
- [ ] HTTPS enforced (no HTTP access)
- [ ] CORS properly configured
- [ ] Authentication working (if enabled)
- [ ] File upload validation working
- [ ] SQL injection protection verified
- [ ] XSS protection enabled

## Production Operations

### Documentation
- [ ] Production deployment guide reviewed
- [ ] Runbook created for common issues
- [ ] Architecture diagram updated
- [ ] API documentation published
- [ ] User guide created
- [ ] Admin procedures documented

### Team Readiness
- [ ] Team trained on deployment process
- [ ] On-call rotation scheduled
- [ ] Escalation procedures defined
- [ ] Access credentials distributed securely
- [ ] Monitoring dashboards shared
- [ ] Incident response plan documented

### Backup & Recovery
- [ ] Database backup schedule configured (daily)
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] Rollback procedure tested
- [ ] Data retention policy defined

### Compliance & Legal
- [ ] Data privacy requirements reviewed
- [ ] Audit logging enabled
- [ ] Terms of service updated
- [ ] Privacy policy available
- [ ] Data residency requirements met
- [ ] GDPR/compliance requirements verified (if applicable)

## Go-Live

### Final Checks
- [ ] All checklist items above completed
- [ ] Stakeholders informed of go-live
- [ ] Support team ready
- [ ] Maintenance window scheduled
- [ ] Communication plan ready
- [ ] Rollback plan ready

### Launch
- [ ] DNS updated (if using custom domain)
- [ ] Traffic routing enabled
- [ ] Monitoring active
- [ ] Team on standby
- [ ] First 10 users tested successfully
- [ ] No critical errors in first hour

### Post-Launch (First 24 Hours)
- [ ] Monitor error rates continuously
- [ ] Check performance metrics
- [ ] Verify user feedback
- [ ] Address any issues immediately
- [ ] Document lessons learned
- [ ] Celebrate success! 🎉

## Monthly Maintenance

### Regular Tasks
- [ ] Review Application Insights analytics
- [ ] Check and optimize costs
- [ ] Update dependencies (npm, pip)
- [ ] Review and rotate secrets
- [ ] Database performance tuning
- [ ] Check disk space usage
- [ ] Review security advisories
- [ ] Backup validation
- [ ] Load test production environment
- [ ] Update documentation

---

## Issue Tracking

| Item | Status | Owner | Due Date | Notes |
|------|--------|-------|----------|-------|
| Example: Azure AI Search setup | ✅ Done | DevOps | 2025-11-24 | Completed |
| | | | | |
| | | | | |

---

## Sign-Off

- [ ] Development Lead: _________________ Date: _______
- [ ] DevOps Engineer: _________________ Date: _______
- [ ] Security Review: _________________ Date: _______
- [ ] Product Owner: _________________ Date: _______

---

**Last Updated:** 2025-11-24

**Next Review Date:** _______

**Production Go-Live Date:** _______
