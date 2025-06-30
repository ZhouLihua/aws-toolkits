 const taskDefinition = new ecs.FargateTaskDefinition(this, `${prefix}TaskDef`, {
      memoryLimitMiB: 1024 * 16, // 16 GB
      cpu: 1024 * 4, // 4 vCPUs
      executionRole: taskExecutionRole,
      taskRole: taskRole,
    });

    // Add shared volume, ephemeral storage
    const sharedVolume = {
      name: 'shared-data',
      host: {},
    };
    taskDefinition.addVolume(sharedVolume);

    const container = taskDefinition.addContainer(`${prefix}Container`, {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'streamlit-app'),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: `${env}-${prefix}-container`,
        logRetention: logs.RetentionDays.TWO_WEEKS,
      }),
      environment: {
        COGNITO_USER_POOL_ID: userPool.userPoolId,
        COGNITO_APP_CLIENT_ID: userPoolClient.userPoolClientId,
        COGNITO_APP_CLIENT_SECRET: userPoolClient.userPoolClientSecret.unsafeUnwrap(),
        TMP_DIR: '/shared-data',
      },
    });

    // Mount shared volume to main container
    container.addMountPoints({
      containerPath: '/shared-data',
      sourceVolume: sharedVolume.name,
      readOnly: false,
    });

    container.addPortMappings({
      containerPort: 8501,
      protocol: ecs.Protocol.TCP,
    });

    // Add sidecar container to clean old files
    const cleanerContainer = taskDefinition.addContainer(`${prefix}CleanerContainer`, {
      image: ecs.ContainerImage.fromRegistry('busybox:stable'),
      command: [
        '/bin/sh',
        '-c',
        'while true; do \
          echo "Starting file cleanup process"; \
          echo "Current disk usage: $(df -h /shared-data)"; \
          echo "Files to be deleted:"; \
          find /shared-data -type f -mtime +1 || echo "No files found"; \
          COUNT=$(find /shared-data -type f -mtime +1 | wc -l); \
          echo "Deleting $COUNT files older than 1 day"; \
          find /shared-data -type f -mtime +1 -delete; \
          echo "Cleanup completed. New disk usage: $(df -h /shared-data)"; \
          echo "Sleeping for 1 hour"; \
          sleep 3600; \
        done',
      ],
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: `${env}-${prefix}-cleaner`,
        logRetention: logs.RetentionDays.TWO_WEEKS,
      }),
      essential: false,
    });

    // Mount shared volume to cleaner container
    cleanerContainer.addMountPoints({
      containerPath: '/shared-data',
      sourceVolume: sharedVolume.name,
      readOnly: false,
    });
