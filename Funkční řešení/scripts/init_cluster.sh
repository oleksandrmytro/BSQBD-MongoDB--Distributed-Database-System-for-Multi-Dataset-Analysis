#!/usr/bin/env sh

# ANSI colors and emojis
RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
NC='\e[0m'  # No Color

ADMIN_USER="st69631"
ADMIN_PASS="password"

echo -e "${BLUE}🔧 Setting execute permissions on helper scripts...${NC}"
chmod +x /scripts/wait-for-it.sh
chmod +x /scripts/import_datasets.sh

echo -e "${BLUE}🚀 Step 2: Initializing replica sets (config server and shards)...${NC}"

echo -e "${YELLOW}⌛ Waiting for configsvr01:27017...${NC}"
/scripts/wait-for-it.sh configsvr01:27017 -t 30

echo -e "${YELLOW}⌛ Waiting for shard-01-node-a:27017...${NC}"
/scripts/wait-for-it.sh shard-01-node-a:27017 -t 30

echo -e "${YELLOW}⌛ Waiting for shard-02-node-a:27017...${NC}"
/scripts/wait-for-it.sh shard-02-node-a:27017 -t 30

echo -e "${YELLOW}⌛ Waiting for shard-03-node-a:27017...${NC}"
/scripts/wait-for-it.sh shard-03-node-a:27017 -t 30

echo -e "${GREEN}🔧 Initializing config server replica set...${NC}"
docker exec mongo-config-01 bash /scripts/init-configserver.js

echo -e "${GREEN}🔧 Initializing Shard 01 replica set...${NC}"
docker exec shard-01-node-a bash /scripts/init-shard01.js

echo -e "${GREEN}🔧 Initializing Shard 02 replica set...${NC}"
docker exec shard-02-node-a bash /scripts/init-shard02.js

echo -e "${GREEN}🔧 Initializing Shard 03 replica set...${NC}"
docker exec shard-03-node-a bash /scripts/init-shard03.js

echo -e "${BLUE}⌛ Waiting 10 seconds for primary election...${NC}"
sleep 10

echo -e "${BLUE}🚀 Step 3: Initializing the router...${NC}"
docker exec router-01 sh -c "mongosh < /scripts/init-router.js"

echo -e "${BLUE}🚀 Step 4: Setting up authentication...${NC}"
docker exec mongo-config-01 bash /scripts/auth.js
docker exec shard-01-node-a bash /scripts/auth.js
docker exec shard-02-node-a bash /scripts/auth.js
docker exec shard-03-node-a bash /scripts/auth.js

echo -e "${BLUE}🚀 Step 5: Enabling sharding and configuring shard keys for collections...${NC}"
cat <<'EOF' | docker exec -i router-01 sh -c "mongosh --port 27017 -u '$ADMIN_USER' --password '$ADMIN_PASS' --authenticationDatabase admin"
use Ecommerce;
sh.enableSharding("Ecommerce");

// APPS_META COLLECTION
if (db.getCollectionNames().includes("apps_meta")) db.apps_meta.drop();
db.createCollection("apps_meta", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "appName", "Category", "Rating", "reviews"],
      properties: {
        _id:       { bsonType: "string", description: "unique app name identifier (App)" },
        appName:   { bsonType: "string", description: "application name" },
        Category:  { bsonType: "string", description: "application category" },
        Rating:    { bsonType: ["double", "null"], minimum: 0, maximum: 5, description: "average rating or null" },
        reviews: {
          bsonType: "array",
          description: "embedded user reviews",
          items: {
            bsonType: "object",
            required: ["App", "Sentiment", "Sentiment_Polarity", "Sentiment_Subjectivity"],
            properties: {
              App:                   { bsonType: "string", description: "application name" },
              Translated_Review:      { bsonType: "string", description: "user review text (optional after update)" },
              Sentiment:              { enum: ["Positive", "Neutral", "Negative"], description: "review sentiment" },
              Sentiment_Polarity:     { bsonType: "double", minimum: -1, maximum: 1, description: "sentiment polarity score" },
              Sentiment_Subjectivity: { bsonType: "double", minimum: 0, maximum: 1, description: "sentiment subjectivity score" }
            }
          }
        }
      }
    }
  },
  validationLevel: "moderate"
});
db.apps_meta.createIndex({ _id: "hashed" });
sh.shardCollection("Ecommerce.apps_meta", { _id: "hashed" }, false, { numInitialChunks: 8 });


// AMAZON COLLECTION
if (db.getCollectionNames().includes("amazon")) db.amazon.drop();
db.createCollection("amazon", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["product_id","product_name","category","price_before_discount","price_after_discount"],
      properties: {
        product_id:           { bsonType: "string",                description: "unique string identifier" },
        product_name:         { bsonType: "string",                description: "product name" },
        category:             { bsonType: "string",                description: "product category" },
        discount_percentage:  { bsonType: ["double","int","null"], minimum: 0, maximum: 100, description: "discount percentage (0–100)" },
        rating:               { bsonType: ["double","null"],     minimum: 0, maximum: 5,   description: "rating between 0 and 5 or null" },
        rating_count:         { bsonType: ["int","null"],        minimum: 0,               description: "number of ratings" },
        price_before_discount:{ bsonType: ["double","int"],      minimum: 0,               description: "price before discount" },
        price_after_discount: { bsonType: ["double","int"],      minimum: 0,               description: "price after discount" }
      }
    }
  },
  validationLevel: "moderate"
});
db.amazon.createIndex({ product_id: "hashed" });
sh.shardCollection("Ecommerce.amazon", { product_id: "hashed" }, false, { numInitialChunks: 8 });

// GOOGLE PLAY STORE COLLECTION
if (db.getCollectionNames().includes("googleplaystore")) db.googleplaystore.drop();
db.createCollection("googleplaystore", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["App","Category","Reviews","Installs","Type","Price"],
      properties: {
        App:            { bsonType: "string",                description: "application name" },
        Category:       { bsonType: "string",                description: "application category" },
        Rating:         { bsonType: ["double","null"],     minimum: 0, maximum: 5,   description: "average rating or null" },
        Reviews:        { bsonType: ["int","null"],        minimum: 0,               description: "number of reviews" },
        Installs:       { bsonType: ["int","null"],        minimum: 0,               description: "number of installs" },
        Type:           { enum: ["Free","Paid"],           description: "application type (Free or Paid)" },
        Price:          { bsonType: "double",                minimum: 0,               description: "price (>= 0)" }
      }
    }
  },
  validationLevel: "moderate"
});
db.googleplaystore.createIndex({ _id: "hashed" });
sh.shardCollection("Ecommerce.googleplaystore", { _id: "hashed" }, false, { numInitialChunks: 4 });

// VIDEO GAME SALES COLLECTION
if (db.getCollectionNames().includes("vgsales")) db.vgsales.drop();
db.createCollection("vgsales", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["Rank","Name","Platform","Year","Genre","Publisher","NA_Sales","EU_Sales","JP_Sales","Other_Sales","Global_Sales"],
      properties: {
        Rank:        { bsonType: "int",            minimum: 1,                description: "sales rank (>= 1)" },
        Name:        { bsonType: ["string","int"], description: "game title or numeric code" },
        Platform:    { bsonType: ["string","int"], description: "gaming platform" },
        Year:        { bsonType: "int",            minimum: 0,                description: "release year" },
        Genre:       { bsonType: "string",                                   description: "game genre" },
        Publisher:   { bsonType: "string",                                   description: "game publisher" },
        NA_Sales:    { bsonType: "double",        minimum: 0,                description: "North America sales (million)" },
        EU_Sales:    { bsonType: "double",        minimum: 0,                description: "Europe sales (million)" },
        JP_Sales:    { bsonType: "double",        minimum: 0,                description: "Japan sales (million)" },
        Other_Sales: { bsonType: "double",        minimum: 0,                description: "Other region sales (million)" },
        Global_Sales:{ bsonType: "double",        minimum: 0,                description: "Global sales (million)" }
      }
    }
  },
  validationLevel: "moderate"
});
db.vgsales.createIndex({ Name: 1, Platform: 1 });
sh.shardCollection("Ecommerce.vgsales", { Name: 1, Platform: 1 }, false);
sh.splitAt("Ecommerce.vgsales", { Name: "M", Platform: MinKey() });
sh.splitAt("Ecommerce.vgsales", { Name: "T", Platform: MinKey() });

// REVIEWS COLLECTION
if (db.getCollectionNames().includes("reviews")) db.reviews.drop();
db.createCollection("reviews", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["App","Translated_Review","Sentiment","Sentiment_Polarity","Sentiment_Subjectivity"],
      properties: {
        App:                   { bsonType: "string",                    description: "application name" },
        Translated_Review:     { bsonType: "string",                    description: "review text" },
        Sentiment:             { enum: ["Positive","Neutral","Negative"], description: "sentiment polarity" },
        Sentiment_Polarity:    { bsonType: "double", minimum: -1, maximum: 1, description: "sentiment score" },
        Sentiment_Subjectivity:{ bsonType: "double", minimum: 0,  maximum: 1, description: "subjectivity score" }
      }
    }
  },
  validationLevel: "moderate"
});
db.reviews.createIndex({ _id: "hashed" });
sh.shardCollection("Ecommerce.reviews", { _id: "hashed" }, false, { numInitialChunks: 8 });

EOF

echo -e "${GREEN}🎉 Cluster initialization complete!${NC}"

