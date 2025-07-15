#!/usr/bin/env bash
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Direct import, Compose depends_on ensures cluster setup before this runs.
echo -e "${YELLOW}Importing amazon.csv into Ecommerce.amazon...${NC}"
mongoimport --host router-01 --port 27017 \
  --username st69631 --password password --authenticationDatabase admin \
  --db Ecommerce --collection amazon --type csv --headerline --file /data/amazon.csv
status=$?

echo -e "${YELLOW}Importing googleplaystore.csv into Ecommerce.googleplaystore...${NC}"
mongoimport --host router-01 --port 27017 \
  --username st69631 --password password --authenticationDatabase admin \
  --db Ecommerce --collection googleplaystore --type csv --headerline --file /data/googleplaystore.csv || status=1

echo -e "${YELLOW}Importing vgsales.csv into Ecommerce.vgsales...${NC}"
mongoimport --host router-01 --port 27017 \
  --username st69631 --password password --authenticationDatabase admin \
  --db Ecommerce --collection vgsales --type csv --headerline --file /data/vgsales.csv || status=1

echo -e "${YELLOW}Importing user reviews into Ecommerce.reviews...${NC}"
mongoimport --host router-01 --port 27017 \
  --username st69631 --password password --authenticationDatabase admin \
  --db Ecommerce --collection reviews --type csv --headerline --file /data/googleplaystore_user_reviews.csv || status=1

echo -e "${YELLOW}Building embedded apps_meta…${NC}"
mongosh --host router-01 --port 27017 \
  -u st69631 -p password --authenticationDatabase admin Ecommerce --quiet --eval '
    db.googleplaystore.aggregate([
      { $lookup:{
          from: "reviews",
          localField: "App",
          foreignField: "App",
          as: "reviews"
      }},
      { $addFields:{ reviews:"$reviews" }},
      { $project:{
          _id:      "$App",
          appName:  "$App",
          Category: 1,
          Rating:   1,
          reviews:  1
      }},
      { $merge:{
          into: "apps_meta",
          whenMatched: "replace",
          whenNotMatched: "insert"
      }}
    ], { allowDiskUse: true });
  '
if [ $status -eq 0 ]; then
  echo -e "${GREEN}🎉 All datasets imported successfully!${NC}"
  exit 0
else
  echo -e "${RED}❌ Data import encountered errors!${NC}"
  exit 1
fi

