# Users scripts

## Migrations.sh

Get permissions
```shell
  chmod +x migrate.sh
```

Start dev docker compose
```shell
 sudo docker compose -f docker-compose.dev.yaml up
```

Start migrations with message

example
```shell
./migrate.sh "your migration message"
```
