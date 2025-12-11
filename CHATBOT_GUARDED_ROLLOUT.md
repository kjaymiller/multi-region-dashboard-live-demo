# Chatbot Guarded Rollout Setup Guide

This guide walks you through setting up a guarded rollout for the Dashboard Chatbot feature flag, following the pattern from the [LaunchDarkly Guarded Releases tutorial](https://launchdarkly.com/docs/tutorials/connecting-rage-clicks-to-guarded-releases).

## Overview

The chatbot feature flag (`dashboard-chatbot-enabled`) is instrumented to track:
1. **Connection Status** - Success/failure of chatbot connections
2. **Message Count** - Number of messages sent
3. **Error Count** - Number of errors encountered
4. **Response Time** - Time taken to get responses (in milliseconds)

## Step 1: Create Metrics in LaunchDarkly

Navigate to **Metrics** → **Create metric** in your LaunchDarkly dashboard.

### Metric 1: Chatbot Connection Status (Occurrence/Binary)

**Configuration:**
- **Event kind**: `Custom`
- **Event key**: `chatbot.connection.status`
- **What do you want to measure?**: **Occurrence** (Binary - tracks successful vs failed connections)
- **Metric name**: `Chatbot - Connection Success Rate`
- **Description**: `Tracks successful vs failed connections to the chatbot service. Monitor for connection failures during rollout.`
- **Tags**: `chatbot`, `connectivity`, `health`
- **Maintainer**: Select yourself

**Click "Create metric"**

### Metric 2: Chatbot Message Count (Count)

**Configuration:**
- **Event kind**: `Custom`
- **Event key**: `chatbot.message.sent`
- **What do you want to measure?**: **Count** (Number of messages sent)
- **Metric name**: `Chatbot - Message Count`
- **Description**: `Tracks the number of messages sent to the chatbot. Use to monitor engagement during rollout.`
- **Tags**: `chatbot`, `engagement`, `usage`
- **Maintainer**: Select yourself

**Click "Create metric"**

### Metric 3: Chatbot Error Count (Count)

**Configuration:**
- **Event kind**: `Custom`
- **Event key**: `chatbot.error`
- **What do you want to measure?**: **Count** (Number of errors)
- **Metric name**: `Chatbot - Error Count`
- **Description**: `Tracks the number of errors encountered when using the chatbot. Alert if this increases significantly during rollout.`
- **Tags**: `chatbot`, `errors`, `reliability`
- **Maintainer**: Select yourself

**Click "Create metric"**

### Metric 4: Chatbot Response Time (Value/Size - Numeric)

**Configuration:**
- **Event kind**: `Custom`
- **Event key**: `chatbot.response.time`
- **What do you want to measure?**: **Value / Size** (Numeric - response time in milliseconds)
- **Metric name**: `Chatbot - Response Time`
- **Description**: `Tracks the response time of the chatbot in milliseconds. Monitor for performance degradation during rollout.`
- **Tags**: `chatbot`, `performance`, `latency`
- **Maintainer**: Select yourself

**Click "Create metric"**

## Step 2: Set Up Guarded Rollout

1. Navigate to your **Dashboard Chatbot Enabled** feature flag (`dashboard-chatbot-enabled`)
2. Go to the **Production** environment (or your target environment)
3. Click **"Add rollout"** or **"Edit rollout"**
4. Select **"Guarded rollout"**

### Guarded Rollout Configuration

#### Rollout Strategy
- **Start with**: `0%` of users
- **Gradually increase to**: `100%` over your desired timeframe (e.g., 1 hour, 1 day)
- **Increment**: `10%` per step (or your preferred increment)

#### Metrics to Monitor

Add all four metrics you created:

1. **Chatbot - Connection Success Rate**
   - **Direction**: "Higher is better"
   - **Alert if**: Connection success rate drops below `95%`
   - **Automatic rollback**: ✓ Enabled
   - **Rollback threshold**: If success rate < `90%`, automatically rollback

2. **Chatbot - Message Count**
   - **Direction**: "Higher is better" (indicates engagement)
   - **Alert if**: Message count decreases by more than `20%` compared to baseline
   - **Automatic rollback**: ⚠️ Optional (you may want to monitor this manually)

3. **Chatbot - Error Count**
   - **Direction**: "Lower is better"
   - **Alert if**: Error count increases by more than `10%` or absolute count > `5` per hour
   - **Automatic rollback**: ✓ Enabled
   - **Rollback threshold**: If error rate > `5%` of total messages, automatically rollback

4. **Chatbot - Response Time**
   - **Direction**: "Lower is better"
   - **Alert if**: Average response time increases by more than `50%` or exceeds `5000ms`
   - **Automatic rollback**: ✓ Enabled
   - **Rollback threshold**: If average response time > `10000ms`, automatically rollback

#### Rollout Schedule

- **Initial**: Start with `0%` (flag OFF)
- **Step 1**: After 5 minutes, enable for `10%` of users
- **Step 2**: After 15 minutes, enable for `25%` of users
- **Step 3**: After 30 minutes, enable for `50%` of users
- **Step 4**: After 1 hour, enable for `75%` of users
- **Step 5**: After 2 hours, enable for `100%` of users

**Note**: Adjust these percentages and timings based on your traffic volume and risk tolerance.

## Step 3: Test the Integration

1. **Enable the flag for yourself** (using a target or individual user context)
2. **Send a test message** through the chatbot
3. **Verify metrics are being tracked**:
   - Go to **Metrics** → Select each metric
   - Check that events are appearing in real-time
4. **Test error scenarios**:
   - Temporarily stop Ollama service
   - Send a message
   - Verify error metrics are tracked

## Step 4: Monitor During Rollout

During the guarded rollout, monitor:

1. **Connection Success Rate**: Should stay above 95%
2. **Error Count**: Should remain low (< 5% of messages)
3. **Response Time**: Should remain reasonable (< 5 seconds average)
4. **Message Count**: Should show healthy engagement

### Alert Thresholds Summary

| Metric | Alert Condition | Rollback Condition |
|--------|----------------|-------------------|
| Connection Success Rate | < 95% | < 90% |
| Error Count | > 10% increase or > 5/hour | > 5% of messages |
| Response Time | > 50% increase or > 5000ms | > 10000ms |
| Message Count | > 20% decrease | Monitor manually |

## Step 5: Rollback Plan

If any metric triggers an automatic rollback:
1. LaunchDarkly will automatically disable the feature for affected users
2. You'll receive an alert notification
3. Investigate the issue:
   - Check Ollama service status
   - Review application logs
   - Check database connectivity
4. Fix the issue before re-enabling the rollout

## Code Implementation

The code is already instrumented in:
- `app/feature_flags.py` - Contains `is_chatbot_enabled()` and `track_chatbot_metric()` functions
- `app/routers/api.py` - Chat endpoint tracks all metrics
- `app/routers/pages.py` - Conditionally renders chatbot UI based on flag
- `app/templates/index.html` - Chatbot UI wrapped in feature flag check

## Additional Metrics (Optional)

You can also track these additional metrics for deeper insights:

### Connection Latency
- **Event key**: `chatbot.connection.latency`
- **Type**: Value/Size (numeric)
- **Description**: Time to establish connection to Ollama

### Reconnection Attempts
- **Event key**: `chatbot.reconnection.attempt`
- **Type**: Count
- **Description**: Number of times users need to reconnect

### Message Length
- **Event key**: `chatbot.message.length`
- **Type**: Value/Size (numeric)
- **Description**: Average length of user messages

## Troubleshooting

### Metrics Not Appearing

1. **Check LaunchDarkly SDK key**: Ensure `LAUNCHDARKLY_SDK_KEY` is set in your environment
2. **Verify flag is enabled**: Check that `dashboard-chatbot-enabled` is ON for your test user
3. **Check event keys**: Ensure event keys match exactly (case-sensitive)
4. **Review application logs**: Look for LaunchDarkly tracking messages

### Connection Failures

1. **Ollama service**: Ensure Ollama is running on `localhost:11434`
2. **Model availability**: Verify `llama3.2:latest` model is available
3. **Network connectivity**: Check firewall rules and network access

## Next Steps

1. ✅ Create all 4 metrics in LaunchDarkly UI
2. ✅ Configure guarded rollout with monitoring thresholds
3. ✅ Test the integration with a small user group
4. ✅ Start the guarded rollout
5. ✅ Monitor metrics and adjust thresholds as needed

For more information, see the [LaunchDarkly Guarded Releases documentation](https://launchdarkly.com/docs/guides/guarded-releases/).


