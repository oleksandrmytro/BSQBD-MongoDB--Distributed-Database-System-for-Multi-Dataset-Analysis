#!/bin/bash

mongosh <<EOF
use admin;
db.createUser({user: "st69631", pwd: "password", roles:[{role: "root", db: "admin"}]});
exit;
EOF
