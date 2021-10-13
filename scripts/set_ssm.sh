aws ssm put-parameter \
    --name "/go-trader/"$1 \
    --value  $2 \
    --type SecureString  \
    --overwrite