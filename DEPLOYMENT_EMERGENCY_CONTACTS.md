# Emergency Contacts and Escalation Procedures

## Primary Deployment Team Contacts

### On-Call Engineers (Rotation)
| Role | Name | Phone | Email | Slack | Timezone |
|------|------|-------|-------|-------|----------|
| Primary On-Call | [Name] | [Phone] | [Email] | @[handle] | [TZ] |
| Secondary On-Call | [Name] | [Phone] | [Email] | @[handle] | [TZ] |
| Backup On-Call | [Name] | [Phone] | [Email] | @[handle] | [TZ] |

### Team Leadership
| Role | Name | Phone | Email | Slack | Available |
|------|------|-------|-------|-------|-----------|
| Technical Lead | [Name] | [Phone] | [Email] | @[handle] | 8am-6pm EST |
| DevOps Lead | [Name] | [Phone] | [Email] | @[handle] | 8am-6pm EST |
| Database Administrator | [Name] | [Phone] | [Email] | @[handle] | 8am-6pm EST |
| Infrastructure Lead | [Name] | [Phone] | [Email] | @[handle] | 8am-6pm EST |

### Management
| Role | Name | Phone | Email | Slack | Available |
|------|------|-------|-------|-------|-----------|
| Engineering Manager | [Name] | [Phone] | [Email] | @[handle] | Business hours |
| CTO | [Name] | [Phone] | [Email] | @[handle] | Emergency only |
| VP Product | [Name] | [Phone] | [Email] | @[handle] | Business hours |

---

## Communication Channels

### Real-Time Communication
- **Slack**: `#sentinelai-incidents` (for incident notifications)
- **Slack**: `#sentinelai-deployments` (for deployment updates)
- **War Room**: Zoom: [zoom-link] | Teams: [teams-link]
- **Bridge Line**: [phone-number] | Passcode: [code]
- **Status Page**: https://status.sentinelai.com (public-facing)
- **Internal Dashboard**: https://internal.sentinelai.com/incidents

### Email Escalation (for documentation)
- **Team**: sentinelai-oncall@company.com
- **Management**: sentinelai-leads@company.com
- **Executives**: engineering-exec@company.com

### External Notification
- **SMS on Critical**: Managed via PagerDuty
- **Call Escalation**: Triggered after 15 minutes unresolved
- **Executive Alert**: Triggered after 30 minutes unresolved

---

## Escalation Matrix

### Level 1: Operational Issue (Error rate 2-5%)

**Notify:** On-call engineer
**Timeframe:** Immediate
**Action:** Investigate and fix forward if possible

```
Trigger: Error rate > 2% and < 5%
├─ Check metrics dashboard
├─ Review recent error logs
├─ Assess impact scope
└─ If fixable in < 5 minutes: Fix forward
   Else: Escalate to Level 2
```

**Escalation Path:**
1. On-call engineer investigates
2. If unresolved in 10 minutes → Notify Tech Lead
3. Document in #sentinelai-incidents

---

### Level 2: Moderate Issue (Error rate 5-10%)

**Notify:** Tech Lead + On-call engineer
**Timeframe:** Within 5 minutes
**Action:** Establish war room, consider rollback

```
Trigger: Error rate > 5% and < 10%
├─ Establish war room
├─ Notify technical lead
├─ Full system investigation
├─ If quick fix (< 15 min): Fix forward
└─ Else: Execute rollback
```

**Response Steps:**
1. Slack message in #sentinelai-incidents with severity
2. If no response within 2 minutes: Page on-call
3. War room established immediately
4. Status updates every 5 minutes

**Slack Template:**
```
:warning: SEVERITY: MODERATE
Error rate: [X]%
Services affected: [list]
Incident commander: @[name]
War room: [zoom-link]
Status page: https://status.sentinelai.com
ETA to resolution: TBD
```

---

### Level 3: Critical Issue (Error rate > 10%)

**Notify:** CTO + Engineering Manager + On-call team
**Timeframe:** Immediate (within 1 minute)
**Action:** Immediate rollback, executive notification

```
Trigger: Error rate > 10%
├─ EXECUTE ROLLBACK IMMEDIATELY
├─ Notify CTO and management
├─ Establish incident war room
├─ Begin RCA
└─ Stakeholder communication
```

**Immediate Response (First 5 minutes):**
1. Call out "CRITICAL INCIDENT" in #sentinelai-incidents
2. Page CTO: `/pagerduty page CTO`
3. Start war room call: [zoom-link]
4. Begin rollback execution
5. Update status page: "Investigating critical issue"

**Slack Critical Alert Template:**
```
:fire: CRITICAL INCIDENT
Error rate: [X]%
Status: [INVESTIGATING | ROLLING BACK | DEGRADED]
Incident commander: @[CTO/Lead]
War room: [zoom-link] | Bridge: [phone]
Status: https://status.sentinelai.com/incidents/[id]
Next update: Every 5 minutes
```

---

## Contact Escalation Sequence

### For Infrastructure/Database Issues
```
Time | Action
-----|--------
T+0  | Contact Primary On-Call Engineer
T+5  | If no response, contact Secondary On-Call
T+10 | Notify Database Administrator
T+15 | Notify Infrastructure Lead
T+20 | Notify Technical Lead
T+30 | Notify CTO
```

### For Application/Code Issues
```
Time | Action
-----|--------
T+0  | Contact Primary On-Call Engineer
T+5  | If no response, contact Secondary On-Call
T+10 | Notify Technical Lead
T+15 | Notify Engineering Manager
T+30 | Notify CTO
```

### For Critical/Multi-System Issues
```
Time | Action
-----|--------
T+0  | Contact CTO directly AND On-call team
T+1  | Notify VP of Product
T+5  | Establish exec bridge
T+15 | Customer notification (if needed)
```

---

## Contact Procedure

### Step 1: Initial Alert (Slack)
1. Post in #sentinelai-incidents with severity level
2. Use appropriate template (see above)
3. Include: error rate, affected services, incident commander

### Step 2: Phone Escalation (if needed)
1. Check on-call rotation: https://pagerduty.com/incidents
2. Call primary on-call directly
3. If no answer within 2 minutes, page through PagerDuty
4. Proceed to next tier if needed

### Step 3: War Room (for Level 2+)
1. Start Zoom call from #sentinelai-incidents pinned link
2. Dial bridge line for audio backup
3. Record call for post-incident analysis
4. Designate one person for status updates

### Step 4: Executive Notification (Level 3 only)
1. CTO notified via PagerDuty
2. VP Engineering notified via Slack
3. VP Product notified (for customer communication)
4. Set up separate exec bridge if needed

---

## During Deployment: Ready Checklist

### 30 Minutes Before Deployment
- [ ] All team members confirmed attending
- [ ] War room link tested and working
- [ ] Bridge line confirmed (dial-in working)
- [ ] Phone numbers available for all participants
- [ ] Chat room established and monitored
- [ ] Status page update drafted
- [ ] On-call team has deployment runbook printed or readily available

### 5 Minutes Before Deployment
- [ ] All participants online and ready
- [ ] Monitoring dashboards visible to team
- [ ] Incident commander identified
- [ ] Rollback procedure reviewed
- [ ] Backup location confirmed
- [ ] Communication channels active

### During Deployment
- [ ] Incident commander running the deployment
- [ ] One person monitoring metrics (separate from deployer)
- [ ] One person managing communications
- [ ] All decisions logged with timestamp
- [ ] Status updates in Slack every 15 minutes
- [ ] War room call remains open throughout

---

## Incident Response Playbook

### Incident Declared (Level 2 or 3)

**Immediate Actions (First 5 minutes):**
1. **Notify** - Post alert in #sentinelai-incidents with severity
2. **Activate** - Open war room and establish bridge
3. **Identify** - Name incident commander
4. **Assess** - Determine scope and impact
5. **Decide** - Rollback vs. fix forward

**Ongoing Actions (Continuous):**
1. **Document** - Record timeline with timestamps
2. **Investigate** - Gather logs, metrics, traces
3. **Communicate** - Update stakeholders every 5-10 minutes
4. **Execute** - Deploy fix or rollback
5. **Verify** - Confirm system recovery

**Resolution Actions (After stabilization):**
1. **Validate** - Verify system metrics normal
2. **Communicate** - Notify stakeholders of resolution
3. **Debrief** - Brief stakeholders on what happened
4. **Document** - Create incident ticket
5. **Schedule** - Schedule RCA for next business day

### Example: Critical Error Rate Spike

**T+0 (Detection)**
- Error rate: 15% (expected: < 2%)
- Alert triggered in monitoring
- Slack notification posted

**T+1 (Response)**
- On-call engineer sees alert
- Posts in #sentinelai-incidents: "CRITICAL: Error rate 15%"
- Calls CTO
- Starts Zoom war room

**T+2 (Assessment)**
- CTO joins war room
- Reviews logs: "Failed database migration"
- Decides: Immediate rollback
- Notifies VP Engineering

**T+3 (Action)**
- Incident commander runs rollback procedure
- Database restore in progress
- Services restarting
- Status page updated: "Investigating critical issue"

**T+10 (Resolution)**
- Services back online
- Error rate: 0.5%
- Status page: "Issue resolved"
- War room continues (RCA)

**T+30 (Post-incident)**
- Incident commander debriefs VP Engineering
- Creates incident ticket
- Schedules RCA for tomorrow 2pm EST
- Team discusses learnings

---

## Communication Templates

### Initial Alert (Slack)
```
:warning: [SEVERITY] Deployment Issue Detected

Service: SentinelAI Production
Severity: [MINOR | MODERATE | CRITICAL]
Error Rate: [X]%
Started: [timestamp]
Status: Investigating
Incident Commander: @[name]
War Room: [zoom-link]
Bridge: [phone] Code: [code]

Affected: [services list]
Impact: [description]
Next Update: [time]
```

### Status Update (Every 5-10 minutes)
```
:clock1: Status Update - [time elapsed]

Status: [INVESTIGATING | ROLLING BACK | FIXING | RECOVERING | RESOLVED]
Error Rate: [X]% (trending [up/down/stable])
Action Taken: [description]
Next Steps: [description]
ETA: [time]
```

### Resolution (End of incident)
```
:checkered_flag: Incident Resolved

Issue: [brief description]
Root Cause: [cause] [will detail in RCA]
Resolution: [action taken]
Recovery Time: [duration]
Status Page: [link]
RCA Scheduled: [date/time]
```

### Post-Incident Follow-up (Next business day)
```
:memo: Incident RCA - [date]

Incident: [name] on [date]
Duration: [time]
Impact: [number of users/transactions affected]
Root Cause: [explanation]
Preventive Measures:
- [measure 1]
- [measure 2]
- [measure 3]

Follow-up Items:
- [ ] Action 1 by @[person] due [date]
- [ ] Action 2 by @[person] due [date]

Full RCA: [link to document]
```

---

## External Communications

### Customer Notification (If needed)
- **Via**: Status page + email notification
- **Timeline**: As soon as incident severity assessed
- **Frequency**: Every 15 minutes during incident
- **Owner**: VP Product (with CTO approval)

### Public Status Page
- Endpoint: https://status.sentinelai.com
- Updates: Automatic from #sentinelai-incidents Slack channel
- Severity levels: Operational | Degraded Performance | Major Outage

### Email Notifications
- All subscribers to status page notified
- Subject: "[INCIDENT] SentinelAI - [severity] - [description]"
- Include: Impact, ETA, mitigation steps

---

## Post-Incident Procedures

### Incident Post-Mortem (RCA - 24-48 hours after)

**Meeting Attendees:**
- Incident Commander
- On-call team members involved
- Technical Lead
- Database Administrator
- Engineering Manager

**Discussion Topics:**
1. Timeline of events
2. Root cause analysis
3. Detection time vs. resolution time
4. Preventive measures
5. Process improvements

**Output:**
- Written RCA document
- 3-5 action items with owners
- Follow-up items tracked in project management

### Knowledge Base Update
- Document the issue and solution
- Update runbooks if procedure was wrong
- Add monitoring to catch similar issues
- Train team on prevention

---

## Useful Resources

### Tools and Dashboards
- Grafana: https://grafana.sentinelai.com/dashboards
- Prometheus: https://prometheus.sentinelai.com
- Logs: https://logs.sentinelai.com (ELK stack)
- Metrics: https://metrics.sentinelai.com
- Status: https://status.sentinelai.com

### Runbooks
- Deployment: `/opt/sentinelai/PRODUCTION_DEPLOYMENT_CHECKLIST.md`
- Procedures: `/opt/sentinelai/PRODUCTION_DEPLOYMENT_PROCEDURES.md`
- Troubleshooting: `/opt/sentinelai/docs/TROUBLESHOOTING.md`

### Slack Channels
- `#sentinelai-incidents` - Active incidents
- `#sentinelai-deployments` - Deployment coordination
- `#sentinelai-oncall` - On-call team discussions
- `#infrastructure` - Infrastructure team
- `#database-team` - Database discussions

### PagerDuty
- URL: https://pagerduty.com/
- On-call schedule: https://pagerduty.com/oncall
- Create incident: https://pagerduty.com/incidents/new
- Escalation policies: https://pagerduty.com/escalation_policies

---

## Drill Procedures (Monthly)

### Monthly Incident Drill
Conducted on first Friday of each month at 10am EST

**Scenario:** Deployment causes 15% error rate

**Drill Steps:**
1. Fake alert posted in #sentinelai-incidents
2. On-call responds and escalates
3. War room opened
4. Team executes full rollback procedure
5. Drill leader evaluates response
6. Lessons learned noted

**Goals:**
- Verify procedures work
- Identify gaps in communication
- Train new team members
- Update contact information if needed

**Outcome:** Drill report filed with any issues found

---

## Final Notes

- **Keep this document updated** with current contact information
- **Test contact procedures quarterly** to ensure they work
- **Review escalation paths annually** or after incidents
- **Update team roster** whenever personnel changes
- **Distribute copies** to all team members before deployments

**Last Updated:** [DATE]
**Next Review:** [DATE]
**Owner:** [TECHNICAL LEAD NAME]
