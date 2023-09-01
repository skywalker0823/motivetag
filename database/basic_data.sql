-- MySQL dump 10.13  Distrib 8.0.29, for macos12 (x86_64)
--
-- Host: 127.0.0.1    Database: motivetag
-- ------------------------------------------------------
-- Server version	8.0.33

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bads`
--

DROP TABLE IF EXISTS `bads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bads` (
  `bad_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  PRIMARY KEY (`bad_id`),
  KEY `member_id` (`member_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `bads_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `bads_ibfk_2` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bads`
--

LOCK TABLES `bads` WRITE;
/*!40000 ALTER TABLE `bads` DISABLE KEYS */;
/*!40000 ALTER TABLE `bads` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `block`
--

DROP TABLE IF EXISTS `block`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `block` (
  `block_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `content_type` varchar(25) DEFAULT NULL,
  `content` text,
  `build_time` datetime DEFAULT NULL,
  `good` int DEFAULT '0',
  `bad` int DEFAULT '0',
  `block_img` varchar(100) DEFAULT NULL,
  `total_score` int DEFAULT '0',
  PRIMARY KEY (`block_id`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `block_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `block`
--

LOCK TABLES `block` WRITE;
/*!40000 ALTER TABLE `block` DISABLE KEYS */;
/*!40000 ALTER TABLE `block` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `block_comment`
--

DROP TABLE IF EXISTS `block_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `block_comment` (
  `comment_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  `content` text,
  `build_time` datetime DEFAULT NULL,
  `nice_comment` int DEFAULT '0',
  `given_score` int DEFAULT '0',
  PRIMARY KEY (`comment_id`),
  KEY `block_id` (`block_id`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `block_comment_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE,
  CONSTRAINT `block_comment_ibfk_2` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `block_comment`
--

LOCK TABLES `block_comment` WRITE;
/*!40000 ALTER TABLE `block_comment` DISABLE KEYS */;
/*!40000 ALTER TABLE `block_comment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `block_tag`
--

DROP TABLE IF EXISTS `block_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `block_tag` (
  `block_tag_id` int NOT NULL AUTO_INCREMENT,
  `block_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`block_tag_id`),
  KEY `block_id` (`block_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `block_tag_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE,
  CONSTRAINT `block_tag_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `block_tag`
--

LOCK TABLES `block_tag` WRITE;
/*!40000 ALTER TABLE `block_tag` DISABLE KEYS */;
/*!40000 ALTER TABLE `block_tag` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brick_discuss`
--

DROP TABLE IF EXISTS `brick_discuss`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brick_discuss` (
  `brick_discuss_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int DEFAULT NULL,
  `brick_id` int DEFAULT NULL,
  `content` text,
  `time` datetime DEFAULT NULL,
  PRIMARY KEY (`brick_discuss_id`),
  KEY `member_id` (`member_id`),
  KEY `brick_id` (`brick_id`),
  CONSTRAINT `brick_discuss_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE SET NULL,
  CONSTRAINT `brick_discuss_ibfk_2` FOREIGN KEY (`brick_id`) REFERENCES `bricks` (`brick_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brick_discuss`
--

LOCK TABLES `brick_discuss` WRITE;
/*!40000 ALTER TABLE `brick_discuss` DISABLE KEYS */;
/*!40000 ALTER TABLE `brick_discuss` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bricks`
--

DROP TABLE IF EXISTS `bricks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bricks` (
  `brick_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int DEFAULT NULL,
  `tag_id` int DEFAULT NULL,
  `title` varchar(100) DEFAULT NULL,
  `content` text,
  `classifi` varchar(100) DEFAULT NULL,
  `feedbacks` int DEFAULT '0',
  `popularity` int DEFAULT '0',
  `time` datetime DEFAULT NULL,
  PRIMARY KEY (`brick_id`),
  KEY `member_id` (`member_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `bricks_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE SET NULL,
  CONSTRAINT `bricks_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bricks`
--

LOCK TABLES `bricks` WRITE;
/*!40000 ALTER TABLE `bricks` DISABLE KEYS */;
/*!40000 ALTER TABLE `bricks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `c_goods`
--

DROP TABLE IF EXISTS `c_goods`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `c_goods` (
  `c_good_id` int NOT NULL AUTO_INCREMENT,
  `comment_id` int NOT NULL,
  `member_id` int NOT NULL,
  PRIMARY KEY (`c_good_id`),
  KEY `member_id` (`member_id`),
  KEY `comment_id` (`comment_id`),
  CONSTRAINT `c_goods_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `c_goods_ibfk_2` FOREIGN KEY (`comment_id`) REFERENCES `block_comment` (`comment_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `c_goods`
--

LOCK TABLES `c_goods` WRITE;
/*!40000 ALTER TABLE `c_goods` DISABLE KEYS */;
/*!40000 ALTER TABLE `c_goods` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `follower`
--

DROP TABLE IF EXISTS `follower`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `follower` (
  `follow_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `follow_who` int NOT NULL,
  PRIMARY KEY (`follow_id`),
  KEY `member_id` (`member_id`),
  KEY `follow_who` (`follow_who`),
  CONSTRAINT `follower_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `follower_ibfk_2` FOREIGN KEY (`follow_who`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `follower`
--

LOCK TABLES `follower` WRITE;
/*!40000 ALTER TABLE `follower` DISABLE KEYS */;
/*!40000 ALTER TABLE `follower` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `friendship`
--

DROP TABLE IF EXISTS `friendship`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `friendship` (
  `friend_ship_id` int NOT NULL AUTO_INCREMENT,
  `request_from` int NOT NULL,
  `request_to` int NOT NULL,
  `status` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`friend_ship_id`),
  KEY `request_from` (`request_from`),
  KEY `request_to` (`request_to`),
  CONSTRAINT `friendship_ibfk_1` FOREIGN KEY (`request_from`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `friendship_ibfk_2` FOREIGN KEY (`request_to`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `friendship`
--

LOCK TABLES `friendship` WRITE;
/*!40000 ALTER TABLE `friendship` DISABLE KEYS */;
/*!40000 ALTER TABLE `friendship` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `goods`
--

DROP TABLE IF EXISTS `goods`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `goods` (
  `good_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  PRIMARY KEY (`good_id`),
  KEY `member_id` (`member_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `goods_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `goods_ibfk_2` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `goods`
--

LOCK TABLES `goods` WRITE;
/*!40000 ALTER TABLE `goods` DISABLE KEYS */;
/*!40000 ALTER TABLE `goods` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `member`
--

DROP TABLE IF EXISTS `member`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `member` (
  `member_id` int NOT NULL AUTO_INCREMENT,
  `account` varchar(50) NOT NULL,
  `password` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `birthday` date DEFAULT NULL,
  `first_signup` date NOT NULL,
  `last_signin` datetime DEFAULT NULL,
  `member_img` varchar(100) DEFAULT NULL,
  `follower` int DEFAULT '0',
  `mood` varchar(100) DEFAULT NULL,
  `exp` int DEFAULT '0',
  PRIMARY KEY (`member_id`),
  UNIQUE KEY `account` (`account`)
) ENGINE=InnoDB AUTO_INCREMENT=5001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `member`
--

LOCK TABLES `member` WRITE;
/*!40000 ALTER TABLE `member` DISABLE KEYS */;
INSERT INTO `member` VALUES (5000,'guest','guest','guest@mail.com',NULL,'1988-09-12',NULL,NULL,0,NULL,0);
/*!40000 ALTER TABLE `member` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `member_tags`
--

DROP TABLE IF EXISTS `member_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `member_tags` (
  `member_tag_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`member_tag_id`),
  KEY `member_id` (`member_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `member_tags_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `member_tags_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `member_tags`
--

LOCK TABLES `member_tags` WRITE;
/*!40000 ALTER TABLE `member_tags` DISABLE KEYS */;
/*!40000 ALTER TABLE `member_tags` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notifi`
--

DROP TABLE IF EXISTS `notifi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifi` (
  `notifi_id` int NOT NULL AUTO_INCREMENT,
  `sender_id` int NOT NULL,
  `reciever_id` int NOT NULL,
  `content` text,
  `send_time` datetime DEFAULT NULL,
  PRIMARY KEY (`notifi_id`),
  KEY `sender_id` (`sender_id`),
  KEY `reciever_id` (`reciever_id`),
  CONSTRAINT `notifi_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `notifi_ibfk_2` FOREIGN KEY (`reciever_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notifi`
--

LOCK TABLES `notifi` WRITE;
/*!40000 ALTER TABLE `notifi` DISABLE KEYS */;
/*!40000 ALTER TABLE `notifi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tag`
--

DROP TABLE IF EXISTS `tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tag` (
  `tag_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `popularity` int DEFAULT NULL,
  `create_date` date DEFAULT NULL,
  `create_by` int DEFAULT NULL,
  `prime_level` int DEFAULT NULL,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `name` (`name`),
  KEY `create_by` (`create_by`),
  CONSTRAINT `tag_ibfk_1` FOREIGN KEY (`create_by`) REFERENCES `member` (`member_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3004 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tag`
--

LOCK TABLES `tag` WRITE;
/*!40000 ALTER TABLE `tag` DISABLE KEYS */;
INSERT INTO `tag` VALUES (3000,'新手引導',0,NULL,NULL,5),(3001,'BroadCast',0,NULL,NULL,3),(3002,'Anonymous',0,NULL,NULL,1),(3003,'MotiveTag',0,NULL,NULL,NULL);
/*!40000 ALTER TABLE `tag` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vote_options`
--

DROP TABLE IF EXISTS `vote_options`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vote_options` (
  `vote_option_id` int NOT NULL AUTO_INCREMENT,
  `block_id` int NOT NULL,
  `best_before` datetime DEFAULT NULL,
  `option_name` text,
  PRIMARY KEY (`vote_option_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `vote_options_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vote_options`
--

LOCK TABLES `vote_options` WRITE;
/*!40000 ALTER TABLE `vote_options` DISABLE KEYS */;
/*!40000 ALTER TABLE `vote_options` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `votes`
--

DROP TABLE IF EXISTS `votes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `votes` (
  `vote_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `vote_option_id` int NOT NULL,
  PRIMARY KEY (`vote_id`),
  KEY `member_id` (`member_id`),
  KEY `vote_option_id` (`vote_option_id`),
  CONSTRAINT `votes_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `votes_ibfk_2` FOREIGN KEY (`vote_option_id`) REFERENCES `vote_options` (`vote_option_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `votes`
--

LOCK TABLES `votes` WRITE;
/*!40000 ALTER TABLE `votes` DISABLE KEYS */;
/*!40000 ALTER TABLE `votes` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-08-23 13:42:57
