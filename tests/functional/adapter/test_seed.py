import csv
from codecs import BOM_UTF8
from pathlib import Path

import pytest
from dbt.tests.adapter.simple_seed.fixtures import (
    models__downstream_from_seed_actual,
    models__from_basic_seed,
)
from dbt.tests.adapter.simple_seed.seeds import (
    seed__actual_csv,
    seed__unicode_csv,
    seed__with_dots_csv,
    seeds__disabled_in_config_csv,
    seeds__enabled_in_config_csv,
    seeds__tricky_csv,
    seeds__wont_parse_csv,
)
from dbt.tests.util import (
    check_relations_equal,
    check_table_does_exist,
    check_table_does_not_exist,
    copy_file,
    mkdir,
    read_file,
    rm_dir,
    run_dbt,
)

seeds__expected_sql = """
create table {schema}.seed_expected (
seed_id int,
first_name varchar(100),
email varchar(50),
ip_address varchar(100),
birthday datetime2(6)
);


INSERT INTO {schema}.seed_expected
    ("seed_id","first_name","email","ip_address","birthday")
VALUES
    (1,'Larry','lking0@miitbeian.gov.cn','69.135.206.194','2008-09-12 19:08:31'),
    (2,'Larry','lperkins1@toplist.cz','64.210.133.162','1978-05-09 04:15:14'),
    (3,'Anna','amontgomery2@miitbeian.gov.cn','168.104.64.114','2011-10-16 04:07:57'),
    (4,'Sandra','sgeorge3@livejournal.com','229.235.252.98','1973-07-19 10:52:43'),
    (5,'Fred','fwoods4@google.cn','78.229.170.124','2012-09-30 16:38:29'),
    (6,'Stephen','shanson5@livejournal.com','182.227.157.105','1995-11-07 21:40:50'),
    (7,'William','wmartinez6@upenn.edu','135.139.249.50','1982-09-05 03:11:59'),
    (8,'Jessica','jlong7@hao123.com','203.62.178.210','1991-10-16 11:03:15'),
    (9,'Douglas','dwhite8@tamu.edu','178.187.247.1','1979-10-01 09:49:48'),
    (10,'Lisa','lcoleman9@nydailynews.com','168.234.128.249','2011-05-26 07:45:49'),
    (11,'Ralph','rfieldsa@home.pl','55.152.163.149','1972-11-18 19:06:11'),
    (12,'Louise','lnicholsb@samsung.com','141.116.153.154','2014-11-25 20:56:14'),
    (13,'Clarence','cduncanc@sfgate.com','81.171.31.133','2011-11-17 07:02:36'),
    (14,'Daniel','dfranklind@omniture.com','8.204.211.37','1980-09-13 00:09:04'),
    (15,'Katherine','klanee@auda.org.au','176.96.134.59','1997-08-22 19:36:56'),
    (16,'Billy','bwardf@wikia.com','214.108.78.85','2003-10-19 02:14:47'),
    (17,'Annie','agarzag@ocn.ne.jp','190.108.42.70','1988-10-28 15:12:35'),
    (18,'Shirley','scolemanh@fastcompany.com','109.251.164.84','1988-08-24 10:50:57'),
    (19,'Roger','rfrazieri@scribd.com','38.145.218.108','1985-12-31 15:17:15'),
    (20,'Lillian','lstanleyj@goodreads.com','47.57.236.17','1970-06-08 02:09:05'),
    (21,'Aaron','arodriguezk@nps.gov','205.245.118.221','1985-10-11 23:07:49'),
    (22,'Patrick','pparkerl@techcrunch.com','19.8.100.182','2006-03-29 12:53:56'),
    (23,'Phillip','pmorenom@intel.com','41.38.254.103','2011-11-07 15:35:43'),
    (24,'Henry','hgarcian@newsvine.com','1.191.216.252','2008-08-28 08:30:44'),
    (25,'Irene','iturnero@opera.com','50.17.60.190','1994-04-01 07:15:02'),
    (26,'Andrew','adunnp@pen.io','123.52.253.176','2000-11-01 06:03:25'),
    (27,'David','dgutierrezq@wp.com','238.23.203.42','1988-01-25 07:29:18'),
    (28,'Henry','hsanchezr@cyberchimps.com','248.102.2.185','1983-01-01 13:36:37'),
    (29,'Evelyn','epetersons@gizmodo.com','32.80.46.119','1979-07-16 17:24:12'),
    (30,'Tammy','tmitchellt@purevolume.com','249.246.167.88','2001-04-03 10:00:23'),
    (31,'Jacqueline','jlittleu@domainmarket.com','127.181.97.47','1986-02-11 21:35:50'),
    (32,'Earl','eortizv@opera.com','166.47.248.240','1996-07-06 08:16:27'),
    (33,'Juan','jgordonw@sciencedirect.com','71.77.2.200','1987-01-31 03:46:44'),
    (34,'Diane','dhowellx@nyu.edu','140.94.133.12','1994-06-11 02:30:05'),
    (35,'Randy','rkennedyy@microsoft.com','73.255.34.196','2005-05-26 20:28:39'),
    (36,'Janice','jriveraz@time.com','22.214.227.32','1990-02-09 04:16:52'),
    (37,'Laura','lperry10@diigo.com','159.148.145.73','2015-03-17 05:59:25'),
    (38,'Gary','gray11@statcounter.com','40.193.124.56','1970-01-27 10:04:51'),
    (39,'Jesse','jmcdonald12@typepad.com','31.7.86.103','2009-03-14 08:14:29'),
    (40,'Sandra','sgonzalez13@goodreads.com','223.80.168.239','1993-05-21 14:08:54'),
    (41,'Scott','smoore14@archive.org','38.238.46.83','1980-08-30 11:16:56'),
    (42,'Phillip','pevans15@cisco.com','158.234.59.34','2011-12-15 23:26:31'),
    (43,'Steven','sriley16@google.ca','90.247.57.68','2011-10-29 19:03:28'),
    (44,'Deborah','dbrown17@hexun.com','179.125.143.240','1995-04-10 14:36:07'),
    (45,'Lori','lross18@ow.ly','64.80.162.180','1980-12-27 16:49:15'),
    (46,'Sean','sjackson19@tumblr.com','240.116.183.69','1988-06-12 21:24:45'),
    (47,'Terry','tbarnes1a@163.com','118.38.213.137','1997-09-22 16:43:19'),
    (48,'Dorothy','dross1b@ebay.com','116.81.76.49','2005-02-28 13:33:24'),
    (49,'Samuel','swashington1c@house.gov','38.191.253.40','1989-01-19 21:15:48'),
    (50,'Ralph','rcarter1d@tinyurl.com','104.84.60.174','2007-08-11 10:21:49'),
    (51,'Wayne','whudson1e@princeton.edu','90.61.24.102','1983-07-03 16:58:12'),
    (52,'Rose','rjames1f@plala.or.jp','240.83.81.10','1995-06-08 11:46:23'),
    (53,'Louise','lcox1g@theglobeandmail.com','105.11.82.145','2016-09-19 14:45:51'),
    (54,'Kenneth','kjohnson1h@independent.co.uk','139.5.45.94','1976-08-17 11:26:19'),
    (55,'Donna','dbrown1i@amazon.co.uk','19.45.169.45','2006-05-27 16:51:40'),
    (56,'Johnny','jvasquez1j@trellian.com','118.202.238.23','1975-11-17 08:42:32'),
    (57,'Patrick','pramirez1k@tamu.edu','231.25.153.198','1997-08-06 11:51:09'),
    (58,'Helen','hlarson1l@prweb.com','8.40.21.39','1993-08-04 19:53:40'),
    (59,'Patricia','pspencer1m@gmpg.org','212.198.40.15','1977-08-03 16:37:27'),
    (60,'Joseph','jspencer1n@marriott.com','13.15.63.238','2005-07-23 20:22:06'),
    (61,'Phillip','pschmidt1o@blogtalkradio.com','177.98.201.190','1976-05-19 21:47:44'),
    (62,'Joan','jwebb1p@google.ru','105.229.170.71','1972-09-07 17:53:47'),
    (63,'Phyllis','pkennedy1q@imgur.com','35.145.8.244','2000-01-01 22:33:37'),
    (64,'Katherine','khunter1r@smh.com.au','248.168.205.32','1991-01-09 06:40:24'),
    (65,'Laura','lvasquez1s@wiley.com','128.129.115.152','1997-10-23 12:04:56'),
    (66,'Juan','jdunn1t@state.gov','44.228.124.51','2004-11-10 05:07:35'),
    (67,'Judith','jholmes1u@wiley.com','40.227.179.115','1977-08-02 17:01:45'),
    (68,'Beverly','bbaker1v@wufoo.com','208.34.84.59','2016-03-06 20:07:23'),
    (69,'Lawrence','lcarr1w@flickr.com','59.158.212.223','1988-09-13 06:07:21'),
    (70,'Gloria','gwilliams1x@mtv.com','245.231.88.33','1995-03-18 22:32:46'),
    (71,'Steven','ssims1y@cbslocal.com','104.50.58.255','2001-08-05 21:26:20'),
    (72,'Betty','bmills1z@arstechnica.com','103.177.214.220','1981-12-14 21:26:54'),
    (73,'Mildred','mfuller20@prnewswire.com','151.158.8.130','2000-04-19 10:13:55'),
    (74,'Donald','dday21@icq.com','9.178.102.255','1972-12-03 00:58:24'),
    (75,'Eric','ethomas22@addtoany.com','85.2.241.227','1992-11-01 05:59:30'),
    (76,'Joyce','jarmstrong23@sitemeter.com','169.224.20.36','1985-10-24 06:50:01'),
    (77,'Maria','mmartinez24@amazonaws.com','143.189.167.135','2005-10-05 05:17:42'),
    (78,'Harry','hburton25@youtube.com','156.47.176.237','1978-03-26 05:53:33'),
    (79,'Kevin','klawrence26@hao123.com','79.136.183.83','1994-10-12 04:38:52'),
    (80,'David','dhall27@prweb.com','133.149.172.153','1976-12-15 16:24:24'),
    (81,'Kathy','kperry28@twitter.com','229.242.72.228','1979-03-04 02:58:56'),
    (82,'Adam','aprice29@elegantthemes.com','13.145.21.10','1982-11-07 11:46:59'),
    (83,'Brandon','bgriffin2a@va.gov','73.249.128.212','2013-10-30 05:30:36'),
    (84,'Henry','hnguyen2b@discovery.com','211.36.214.242','1985-01-09 06:37:27'),
    (85,'Eric','esanchez2c@edublogs.org','191.166.188.251','2004-05-01 23:21:42'),
    (86,'Jason','jlee2d@jimdo.com','193.92.16.182','1973-01-08 09:05:39'),
    (87,'Diana','drichards2e@istockphoto.com','19.130.175.245','1994-10-05 22:50:49'),
    (88,'Andrea','awelch2f@abc.net.au','94.155.233.96','2002-04-26 08:41:44'),
    (89,'Louis','lwagner2g@miitbeian.gov.cn','26.217.34.111','2003-08-25 07:56:39'),
    (90,'Jane','jsims2h@seesaa.net','43.4.220.135','1987-03-20 20:39:04'),
    (91,'Larry','lgrant2i@si.edu','97.126.79.34','2000-09-07 20:26:19'),
    (92,'Louis','ldean2j@prnewswire.com','37.148.40.127','2011-09-16 20:12:14'),
    (93,'Jennifer','jcampbell2k@xing.com','38.106.254.142','1988-07-15 05:06:49'),
    (94,'Wayne','wcunningham2l@google.com.hk','223.28.26.187','2009-12-15 06:16:54'),
    (95,'Lori','lstevens2m@icq.com','181.250.181.58','1984-10-28 03:29:19'),
    (96,'Judy','jsimpson2n@marriott.com','180.121.239.219','1986-02-07 15:18:10'),
    (97,'Phillip','phoward2o@usa.gov','255.247.0.175','2002-12-26 08:44:45'),
    (98,'Gloria','gwalker2p@usa.gov','156.140.7.128','1997-10-04 07:58:58'),
    (99,'Paul','pjohnson2q@umn.edu','183.59.198.197','1991-11-14 12:33:55'),
    (100,'Frank','fgreene2r@blogspot.com','150.143.68.121','2010-06-12 23:55:39'),
    (101,'Deborah','dknight2s@reverbnation.com','222.131.211.191','1970-07-08 08:54:23'),
    (102,'Sandra','sblack2t@tripadvisor.com','254.183.128.254','2000-04-12 02:39:36'),
    (103,'Edward','eburns2u@dailymotion.com','253.89.118.18','1993-10-10 10:54:01'),
    (104,'Anthony','ayoung2v@ustream.tv','118.4.193.176','1978-08-26 17:07:29'),
    (105,'Donald','dlawrence2w@wp.com','139.200.159.227','2007-07-21 20:56:20'),
    (106,'Matthew','mfreeman2x@google.fr','205.26.239.92','2014-12-05 17:05:39'),
    (107,'Sean','ssanders2y@trellian.com','143.89.82.108','1993-07-14 21:45:02'),
    (108,'Sharon','srobinson2z@soundcloud.com','66.234.247.54','1977-04-06 19:07:03'),
    (109,'Jennifer','jwatson30@t-online.de','196.102.127.7','1998-03-07 05:12:23'),
    (110,'Clarence','cbrooks31@si.edu','218.93.234.73','2002-11-06 17:22:25'),
    (111,'Jose','jflores32@goo.gl','185.105.244.231','1995-01-05 06:32:21'),
    (112,'George','glee33@adobe.com','173.82.249.196','2015-01-04 02:47:46'),
    (113,'Larry','lhill34@linkedin.com','66.5.206.195','2010-11-02 10:21:17'),
    (114,'Marie','mmeyer35@mysql.com','151.152.88.107','1990-05-22 20:52:51'),
    (115,'Clarence','cwebb36@skype.com','130.198.55.217','1972-10-27 07:38:54'),
    (116,'Sarah','scarter37@answers.com','80.89.18.153','1971-08-24 19:29:30'),
    (117,'Henry','hhughes38@webeden.co.uk','152.60.114.174','1973-01-27 09:00:42'),
    (118,'Teresa','thenry39@hao123.com','32.187.239.106','2015-11-06 01:48:44'),
    (119,'Billy','bgutierrez3a@sun.com','52.37.70.134','2002-03-19 03:20:19'),
    (120,'Anthony','agibson3b@github.io','154.251.232.213','1991-04-19 01:08:15'),
    (121,'Sandra','sromero3c@wikia.com','44.124.171.2','1998-09-06 20:30:34'),
    (122,'Paula','pandrews3d@blogs.com','153.142.118.226','2003-06-24 16:31:24'),
    (123,'Terry','tbaker3e@csmonitor.com','99.120.45.219','1970-12-09 23:57:21'),
    (124,'Lois','lwilson3f@reuters.com','147.44.171.83','1971-01-09 22:28:51'),
    (125,'Sara','smorgan3g@nature.com','197.67.192.230','1992-01-28 20:33:24'),
    (126,'Charles','ctorres3h@china.com.cn','156.115.216.2','1993-10-02 19:36:34'),
    (127,'Richard','ralexander3i@marriott.com','248.235.180.59','1999-02-03 18:40:55'),
    (128,'Christina','charper3j@cocolog-nifty.com','152.114.116.129','1978-09-13 00:37:32'),
    (129,'Steve','sadams3k@economist.com','112.248.91.98','2004-03-21 09:07:43'),
    (130,'Katherine','krobertson3l@ow.ly','37.220.107.28','1977-03-18 19:28:50'),
    (131,'Donna','dgibson3m@state.gov','222.218.76.221','1999-02-01 06:46:16'),
    (132,'Christina','cwest3n@mlb.com','152.114.6.160','1979-12-24 15:30:35'),
    (133,'Sandra','swillis3o@meetup.com','180.71.49.34','1984-09-27 08:05:54'),
    (134,'Clarence','cedwards3p@smugmug.com','10.64.180.186','1979-04-16 16:52:10'),
    (135,'Ruby','rjames3q@wp.com','98.61.54.20','2007-01-13 14:25:52'),
    (136,'Sarah','smontgomery3r@tripod.com','91.45.164.172','2009-07-25 04:34:30'),
    (137,'Sarah','soliver3s@eventbrite.com','30.106.39.146','2012-05-09 22:12:33'),
    (138,'Deborah','dwheeler3t@biblegateway.com','59.105.213.173','1999-11-09 08:08:44'),
    (139,'Deborah','dray3u@i2i.jp','11.108.186.217','2014-02-04 03:15:19'),
    (140,'Paul','parmstrong3v@alexa.com','6.250.59.43','2009-12-21 10:08:53'),
    (141,'Aaron','abishop3w@opera.com','207.145.249.62','1996-04-25 23:20:23'),
    (142,'Henry','hsanders3x@google.ru','140.215.203.171','2012-01-29 11:52:32'),
    (143,'Anne','aanderson3y@1688.com','74.150.102.118','1982-04-03 13:46:17'),
    (144,'Victor','vmurphy3z@hugedomains.com','222.155.99.152','1987-11-03 19:58:41'),
    (145,'Evelyn','ereid40@pbs.org','249.122.33.117','1977-12-14 17:09:57'),
    (146,'Brian','bgonzalez41@wikia.com','246.254.235.141','1991-02-24 00:45:58'),
    (147,'Sandra','sgray42@squarespace.com','150.73.28.159','1972-07-28 17:26:32'),
    (148,'Alice','ajones43@a8.net','78.253.12.177','2002-12-05 16:57:46'),
    (149,'Jessica','jhanson44@mapquest.com','87.229.30.160','1994-01-30 11:40:04'),
    (150,'Louise','lbailey45@reuters.com','191.219.31.101','2011-09-07 21:11:45'),
    (151,'Christopher','cgonzalez46@printfriendly.com','83.137.213.239','1984-10-24 14:58:04'),
    (152,'Gregory','gcollins47@yandex.ru','28.176.10.115','1998-07-25 17:17:10'),
    (153,'Jane','jperkins48@usnews.com','46.53.164.159','1979-08-19 15:25:00'),
    (154,'Phyllis','plong49@yahoo.co.jp','208.140.88.2','1985-07-06 02:16:36'),
    (155,'Adam','acarter4a@scribd.com','78.48.148.204','2005-07-20 03:31:09'),
    (156,'Frank','fweaver4b@angelfire.com','199.180.255.224','2011-03-04 23:07:54'),
    (157,'Ronald','rmurphy4c@cloudflare.com','73.42.97.231','1991-01-11 10:39:41'),
    (158,'Richard','rmorris4d@e-recht24.de','91.9.97.223','2009-01-17 21:05:15'),
    (159,'Rose','rfoster4e@woothemes.com','203.169.53.16','1991-04-21 02:09:38'),
    (160,'George','ggarrett4f@uiuc.edu','186.61.5.167','1989-11-11 11:29:42'),
    (161,'Victor','vhamilton4g@biblegateway.com','121.229.138.38','2012-06-22 18:01:23'),
    (162,'Mark','mbennett4h@businessinsider.com','209.184.29.203','1980-04-16 15:26:34'),
    (163,'Martin','mwells4i@ifeng.com','97.223.55.105','2010-05-26 14:08:18'),
    (164,'Diana','dstone4j@google.ru','90.155.52.47','2013-02-11 00:14:54'),
    (165,'Walter','wferguson4k@blogger.com','30.63.212.44','1986-02-20 17:46:46'),
    (166,'Denise','dcoleman4l@vistaprint.com','10.209.153.77','1992-05-13 20:14:14'),
    (167,'Philip','pknight4m@xing.com','15.28.135.167','2000-09-11 18:41:13'),
    (168,'Russell','rcarr4n@youtube.com','113.55.165.50','2008-07-10 17:49:27'),
    (169,'Donna','dburke4o@dion.ne.jp','70.0.105.111','1992-02-10 17:24:58'),
    (170,'Anne','along4p@squidoo.com','36.154.58.107','2012-08-19 23:35:31'),
    (171,'Clarence','cbanks4q@webeden.co.uk','94.57.53.114','1972-03-11 21:46:44'),
    (172,'Betty','bbowman4r@cyberchimps.com','178.115.209.69','2013-01-13 21:34:51'),
    (173,'Andrew','ahudson4s@nytimes.com','84.32.252.144','1998-09-15 14:20:04'),
    (174,'Keith','kgordon4t@cam.ac.uk','189.237.211.102','2009-01-22 05:34:38'),
    (175,'Patrick','pwheeler4u@mysql.com','47.22.117.226','1984-09-05 22:33:15'),
    (176,'Jesse','jfoster4v@mapquest.com','229.95.131.46','1990-01-20 12:19:15'),
    (177,'Arthur','afisher4w@jugem.jp','107.255.244.98','1983-10-13 11:08:46'),
    (178,'Nicole','nryan4x@wsj.com','243.211.33.221','1974-05-30 23:19:14'),
    (179,'Bruce','bjohnson4y@sfgate.com','17.41.200.101','1992-09-23 02:02:19'),
    (180,'Terry','tcox4z@reference.com','20.189.120.106','1982-02-13 12:43:14'),
    (181,'Ashley','astanley50@kickstarter.com','86.3.56.98','1976-05-09 01:27:16'),
    (182,'Michael','mrivera51@about.me','72.118.249.0','1971-11-11 17:28:37'),
    (183,'Steven','sgonzalez52@mozilla.org','169.112.247.47','2002-08-24 14:59:25'),
    (184,'Kathleen','kfuller53@bloglovin.com','80.93.59.30','2002-03-11 13:41:29'),
    (185,'Nicole','nhenderson54@usda.gov','39.253.60.30','1995-04-24 05:55:07'),
    (186,'Ralph','rharper55@purevolume.com','167.147.142.189','1980-02-10 18:35:45'),
    (187,'Heather','hcunningham56@photobucket.com','96.222.196.229','2007-06-15 05:37:50'),
    (188,'Nancy','nlittle57@cbc.ca','241.53.255.175','2007-07-12 23:42:48'),
    (189,'Juan','jramirez58@pinterest.com','190.128.84.27','1978-11-07 23:37:37'),
    (190,'Beverly','bfowler59@chronoengine.com','54.144.230.49','1979-03-31 23:27:28'),
    (191,'Shirley','sstevens5a@prlog.org','200.97.231.248','2011-12-06 07:08:50'),
    (192,'Annie','areyes5b@squidoo.com','223.32.182.101','2011-05-28 02:42:09'),
    (193,'Jack','jkelley5c@tiny.cc','47.34.118.150','1981-12-05 17:31:40'),
    (194,'Keith','krobinson5d@1und1.de','170.210.209.31','1999-03-09 11:05:43'),
    (195,'Joseph','jmiller5e@google.com.au','136.74.212.139','1984-10-08 13:18:20'),
    (196,'Annie','aday5f@blogspot.com','71.99.186.69','1986-02-18 12:27:34'),
    (197,'Nancy','nperez5g@liveinternet.ru','28.160.6.107','1983-10-20 17:51:20'),
    (198,'Tammy','tward5h@ucoz.ru','141.43.164.70','1980-03-31 04:45:29'),
    (199,'Doris','dryan5i@ted.com','239.117.202.188','1985-07-03 03:17:53'),
    (200,'Rose','rmendoza5j@photobucket.com','150.200.206.79','1973-04-21 21:36:40'),
    (201,'Cynthia','cbutler5k@hubpages.com','80.153.174.161','2001-01-20 01:42:26'),
    (202,'Samuel','soliver5l@people.com.cn','86.127.246.140','1970-09-02 02:19:00'),
    (203,'Carl','csanchez5m@mysql.com','50.149.237.107','1993-12-01 07:02:09'),
    (204,'Kathryn','kowens5n@geocities.jp','145.166.205.201','2004-07-06 18:39:33'),
    (205,'Nicholas','nnichols5o@parallels.com','190.240.66.170','2014-11-11 18:52:19'),
    (206,'Keith','kwillis5p@youtube.com','181.43.206.100','1998-06-13 06:30:51'),
    (207,'Justin','jwebb5q@intel.com','211.54.245.74','2000-11-04 16:58:26'),
    (208,'Gary','ghicks5r@wikipedia.org','196.154.213.104','1992-12-01 19:48:28'),
    (209,'Martin','mpowell5s@flickr.com','153.67.12.241','1983-06-30 06:24:32'),
    (210,'Brenda','bkelley5t@xinhuanet.com','113.100.5.172','2005-01-08 20:50:22'),
    (211,'Edward','eray5u@a8.net','205.187.246.65','2011-09-26 08:04:44'),
    (212,'Steven','slawson5v@senate.gov','238.150.250.36','1978-11-22 02:48:09'),
    (213,'Robert','rthompson5w@furl.net','70.7.89.236','2001-09-12 08:52:07'),
    (214,'Jack','jporter5x@diigo.com','220.172.29.99','1976-07-26 14:29:21'),
    (215,'Lisa','ljenkins5y@oakley.com','150.151.170.180','2010-03-20 19:21:16'),
    (216,'Theresa','tbell5z@mayoclinic.com','247.25.53.173','2001-03-11 05:36:40'),
    (217,'Jimmy','jstephens60@weather.com','145.101.93.235','1983-04-12 09:35:30'),
    (218,'Louis','lhunt61@amazon.co.jp','78.137.6.253','1997-08-29 19:34:34'),
    (219,'Lawrence','lgilbert62@ted.com','243.132.8.78','2015-04-08 22:06:56'),
    (220,'David','dgardner63@4shared.com','204.40.46.136','1971-07-09 03:29:11'),
    (221,'Charles','ckennedy64@gmpg.org','211.83.233.2','2011-02-26 11:55:04'),
    (222,'Lillian','lbanks65@msu.edu','124.233.12.80','2010-05-16 20:29:02'),
    (223,'Ernest','enguyen66@baidu.com','82.45.128.148','1996-07-04 10:07:04'),
    (224,'Ryan','rrussell67@cloudflare.com','202.53.240.223','1983-08-05 12:36:29'),
    (225,'Donald','ddavis68@ustream.tv','47.39.218.137','1989-05-27 02:30:56'),
    (226,'Joe','jscott69@blogspot.com','140.23.131.75','1973-03-16 12:21:31'),
    (227,'Anne','amarshall6a@google.ca','113.162.200.197','1988-12-09 03:38:29'),
    (228,'Willie','wturner6b@constantcontact.com','85.83.182.249','1991-10-06 01:51:10'),
    (229,'Nicole','nwilson6c@sogou.com','30.223.51.135','1977-05-29 19:54:56'),
    (230,'Janet','jwheeler6d@stumbleupon.com','153.194.27.144','2011-03-13 12:48:47'),
    (231,'Lois','lcarr6e@statcounter.com','0.41.36.53','1993-02-06 04:52:01'),
    (232,'Shirley','scruz6f@tmall.com','37.156.39.223','2007-02-18 17:47:01'),
    (233,'Patrick','pford6g@reverbnation.com','36.198.200.89','1977-03-06 15:47:24'),
    (234,'Lisa','lhudson6h@usatoday.com','134.213.58.137','2014-10-28 01:56:56'),
    (235,'Pamela','pmartinez6i@opensource.org','5.151.127.202','1987-11-30 16:44:47'),
    (236,'Larry','lperez6j@infoseek.co.jp','235.122.96.148','1979-01-18 06:33:45'),
    (237,'Pamela','pramirez6k@census.gov','138.233.34.163','2012-01-29 10:35:20'),
    (238,'Daniel','dcarr6l@php.net','146.21.152.242','1984-11-17 08:22:59'),
    (239,'Patrick','psmith6m@indiegogo.com','136.222.199.36','2001-05-30 22:16:44'),
    (240,'Raymond','rhenderson6n@hc360.com','116.31.112.38','2000-01-05 20:35:41'),
    (241,'Teresa','treynolds6o@miitbeian.gov.cn','198.126.205.220','1996-11-08 01:27:31'),
    (242,'Johnny','jmason6p@flickr.com','192.8.232.114','2013-05-14 05:35:50'),
    (243,'Angela','akelly6q@guardian.co.uk','234.116.60.197','1977-08-20 02:05:17'),
    (244,'Douglas','dcole6r@cmu.edu','128.135.212.69','2016-10-26 17:40:36'),
    (245,'Frances','fcampbell6s@twitpic.com','94.22.243.235','1987-04-26 07:07:13'),
    (246,'Donna','dgreen6t@chron.com','227.116.46.107','2011-07-25 12:59:54'),
    (247,'Benjamin','bfranklin6u@redcross.org','89.141.142.89','1974-05-03 20:28:18'),
    (248,'Randy','rpalmer6v@rambler.ru','70.173.63.178','2011-12-20 17:40:18'),
    (249,'Melissa','mmurray6w@bbb.org','114.234.118.137','1991-02-26 12:45:44'),
    (250,'Jean','jlittle6x@epa.gov','141.21.163.254','1991-08-16 04:57:09'),
    (251,'Daniel','dolson6y@nature.com','125.75.104.97','2010-04-23 06:25:54'),
    (252,'Kathryn','kwells6z@eventbrite.com','225.104.28.249','2015-01-31 02:21:50'),
    (253,'Theresa','tgonzalez70@ox.ac.uk','91.93.156.26','1971-12-11 10:31:31'),
    (254,'Beverly','broberts71@bluehost.com','244.40.158.89','2013-09-21 13:02:31'),
    (255,'Pamela','pmurray72@netscape.com','218.54.95.216','1985-04-16 00:34:00'),
    (256,'Timothy','trichardson73@amazonaws.com','235.49.24.229','2000-11-11 09:48:28'),
    (257,'Mildred','mpalmer74@is.gd','234.125.95.132','1992-05-25 02:25:02'),
    (258,'Jessica','jcampbell75@google.it','55.98.30.140','2014-08-26 00:26:34'),
    (259,'Beverly','bthomas76@cpanel.net','48.78.228.176','1970-08-18 10:40:05'),
    (260,'Eugene','eward77@cargocollective.com','139.226.204.2','1996-12-04 23:17:00'),
    (261,'Andrea','aallen78@webnode.com','160.31.214.38','2009-07-06 07:22:37'),
    (262,'Justin','jruiz79@merriam-webster.com','150.149.246.122','2005-06-06 11:44:19'),
    (263,'Kenneth','kedwards7a@networksolutions.com','98.82.193.128','2001-07-03 02:00:10'),
    (264,'Rachel','rday7b@miibeian.gov.cn','114.15.247.221','1994-08-18 19:45:40'),
    (265,'Russell','rmiller7c@instagram.com','184.130.152.253','1977-11-06 01:58:12'),
    (266,'Bonnie','bhudson7d@cornell.edu','235.180.186.206','1990-12-03 22:45:24'),
    (267,'Raymond','rknight7e@yandex.ru','161.2.44.252','1995-08-25 04:31:19'),
    (268,'Bonnie','brussell7f@elpais.com','199.237.57.207','1991-03-29 08:32:06'),
    (269,'Marie','mhenderson7g@elpais.com','52.203.131.144','2004-06-04 21:50:28'),
    (270,'Alan','acarr7h@trellian.com','147.51.205.72','2005-03-03 10:51:31'),
    (271,'Barbara','bturner7i@hugedomains.com','103.160.110.226','2004-08-04 13:42:40'),
    (272,'Christina','cdaniels7j@census.gov','0.238.61.251','1972-10-18 12:47:33'),
    (273,'Jeremy','jgomez7k@reuters.com','111.26.65.56','2013-01-13 10:41:35'),
    (274,'Laura','lwood7l@icio.us','149.153.38.205','2011-06-25 09:33:59'),
    (275,'Matthew','mbowman7m@auda.org.au','182.138.206.172','1999-03-05 03:25:36'),
    (276,'Denise','dparker7n@icq.com','0.213.88.138','2011-11-04 09:43:06'),
    (277,'Phillip','pparker7o@discuz.net','219.242.165.240','1973-10-19 04:22:29'),
    (278,'Joan','jpierce7p@salon.com','63.31.213.202','1989-04-09 22:06:24'),
    (279,'Irene','ibaker7q@cbc.ca','102.33.235.114','1992-09-04 13:00:57'),
    (280,'Betty','bbowman7r@ted.com','170.91.249.242','2015-09-28 08:14:22'),
    (281,'Teresa','truiz7s@boston.com','82.108.158.207','1999-07-18 05:17:09'),
    (282,'Helen','hbrooks7t@slideshare.net','102.87.162.187','2003-01-06 15:45:29'),
    (283,'Karen','kgriffin7u@wunderground.com','43.82.44.184','2010-05-28 01:56:37'),
    (284,'Lisa','lfernandez7v@mtv.com','200.238.218.220','1993-04-03 20:33:51'),
    (285,'Jesse','jlawrence7w@timesonline.co.uk','95.122.105.78','1990-01-05 17:28:43'),
    (286,'Terry','tross7x@macromedia.com','29.112.114.133','2009-08-29 21:32:17'),
    (287,'Angela','abradley7y@icq.com','177.44.27.72','1989-10-04 21:46:06'),
    (288,'Maria','mhart7z@dailymotion.com','55.27.55.202','1975-01-21 01:22:57'),
    (289,'Raymond','randrews80@pinterest.com','88.90.78.67','1992-03-16 21:37:40'),
    (290,'Kathy','krice81@bluehost.com','212.63.196.102','2000-12-14 03:06:44'),
    (291,'Cynthia','cramos82@nymag.com','107.89.190.6','2005-06-28 02:02:33'),
    (292,'Kimberly','kjones83@mysql.com','86.169.101.101','2007-06-13 22:56:49'),
    (293,'Timothy','thansen84@microsoft.com','108.100.254.90','2003-04-04 10:31:57'),
    (294,'Carol','cspencer85@berkeley.edu','75.118.144.187','1999-03-30 14:53:21'),
    (295,'Louis','lmedina86@latimes.com','141.147.163.24','1991-04-11 17:53:13'),
    (296,'Margaret','mcole87@google.fr','53.184.26.83','1991-12-19 01:54:10'),
    (297,'Mary','mgomez88@yellowpages.com','208.56.57.99','1976-05-21 18:05:08'),
    (298,'Amanda','aanderson89@geocities.com','147.73.15.252','1987-08-22 15:05:28'),
    (299,'Kathryn','kgarrett8a@nature.com','27.29.177.220','1976-07-15 04:25:04'),
    (300,'Dorothy','dmason8b@shareasale.com','106.210.99.193','1990-09-03 21:39:31'),
    (301,'Lois','lkennedy8c@amazon.de','194.169.29.187','2007-07-29 14:09:31'),
    (302,'Irene','iburton8d@washingtonpost.com','196.143.110.249','2013-09-05 11:32:46'),
    (303,'Betty','belliott8e@wired.com','183.105.222.199','1979-09-19 19:29:13'),
    (304,'Bobby','bmeyer8f@census.gov','36.13.161.145','2014-05-24 14:34:39'),
    (305,'Ann','amorrison8g@sfgate.com','72.154.54.137','1978-10-05 14:22:34'),
    (306,'Daniel','djackson8h@wunderground.com','144.95.32.34','1990-07-27 13:23:05'),
    (307,'Joe','jboyd8i@alibaba.com','187.105.86.178','2011-09-28 16:46:32'),
    (308,'Ralph','rdunn8j@fc2.com','3.19.87.255','1984-10-18 08:00:40'),
    (309,'Craig','ccarter8k@gizmodo.com','235.152.76.215','1998-07-04 12:15:21'),
    (310,'Paula','pdean8l@hhs.gov','161.100.173.197','1973-02-13 09:38:55'),
    (311,'Andrew','agarrett8m@behance.net','199.253.123.218','1991-02-14 13:36:32'),
    (312,'Janet','jhowell8n@alexa.com','39.189.139.79','2012-11-24 20:17:33'),
    (313,'Keith','khansen8o@godaddy.com','116.186.223.196','1987-08-23 21:22:05'),
    (314,'Nicholas','nedwards8p@state.gov','142.175.142.11','1977-03-28 18:27:27'),
    (315,'Jacqueline','jallen8q@oaic.gov.au','189.66.135.192','1994-10-26 11:44:26'),
    (316,'Frank','fgardner8r@mapy.cz','154.77.119.169','1983-01-29 19:19:51'),
    (317,'Eric','eharrison8s@google.cn','245.139.65.123','1984-02-04 09:54:36'),
    (318,'Gregory','gcooper8t@go.com','171.147.0.221','2004-06-14 05:22:08'),
    (319,'Jean','jfreeman8u@rakuten.co.jp','67.243.121.5','1977-01-07 18:23:43'),
    (320,'Juan','jlewis8v@shinystat.com','216.181.171.189','2001-08-23 17:32:43'),
    (321,'Randy','rwilliams8w@shinystat.com','105.152.146.28','1983-02-17 00:05:50'),
    (322,'Stephen','shart8x@sciencedirect.com','196.131.205.148','2004-02-15 10:12:03'),
    (323,'Annie','ahunter8y@example.com','63.36.34.103','2003-07-23 21:15:25'),
    (324,'Melissa','mflores8z@cbc.ca','151.230.217.90','1983-11-02 14:53:56'),
    (325,'Jane','jweaver90@about.me','0.167.235.217','1987-07-29 00:13:44'),
    (326,'Anthony','asmith91@oracle.com','97.87.48.41','2001-05-31 18:44:11'),
    (327,'Terry','tdavis92@buzzfeed.com','46.20.12.51','2015-09-12 23:13:55'),
    (328,'Brandon','bmontgomery93@gravatar.com','252.101.48.186','2010-10-28 08:26:27'),
    (329,'Chris','cmurray94@bluehost.com','25.158.167.97','2004-05-05 16:10:31'),
    (330,'Denise','dfuller95@hugedomains.com','216.210.149.28','1979-04-20 08:57:24'),
    (331,'Arthur','amcdonald96@sakura.ne.jp','206.42.36.213','2009-08-15 03:26:16'),
    (332,'Jesse','jhoward97@google.cn','46.181.118.30','1974-04-18 14:08:41'),
    (333,'Frank','fsimpson98@domainmarket.com','163.220.211.87','2006-06-30 14:46:52'),
    (334,'Janice','jwoods99@pen.io','229.245.237.182','1988-04-06 11:52:58'),
    (335,'Rebecca','rroberts9a@huffingtonpost.com','148.96.15.80','1976-10-05 08:44:16'),
    (336,'Joshua','jray9b@opensource.org','192.253.12.198','1971-12-25 22:27:07'),
    (337,'Joyce','jcarpenter9c@statcounter.com','125.171.46.215','2001-12-31 22:08:13'),
    (338,'Andrea','awest9d@privacy.gov.au','79.101.180.201','1983-02-18 20:07:47'),
    (339,'Christine','chudson9e@yelp.com','64.198.43.56','1997-09-08 08:03:43'),
    (340,'Joe','jparker9f@earthlink.net','251.215.148.153','1973-11-04 05:08:18'),
    (341,'Thomas','tkim9g@answers.com','49.187.34.47','1991-08-07 21:13:48'),
    (342,'Janice','jdean9h@scientificamerican.com','4.197.117.16','2009-12-08 02:35:49'),
    (343,'James','jmitchell9i@umich.edu','43.121.18.147','2011-04-28 17:04:09'),
    (344,'Charles','cgardner9j@purevolume.com','197.78.240.240','1998-02-11 06:47:07'),
    (345,'Robert','rhenderson9k@friendfeed.com','215.84.180.88','2002-05-10 15:33:14'),
    (346,'Chris','cgray9l@4shared.com','249.70.192.240','1998-10-03 16:43:42'),
    (347,'Gloria','ghayes9m@hibu.com','81.103.138.26','1999-12-26 11:23:13'),
    (348,'Edward','eramirez9n@shareasale.com','38.136.90.136','2010-08-19 08:01:06'),
    (349,'Cheryl','cbutler9o@google.ca','172.180.78.172','1995-05-27 20:03:52'),
    (350,'Margaret','mwatkins9p@sfgate.com','3.20.198.6','2014-10-21 01:42:58'),
    (351,'Rebecca','rwelch9q@examiner.com','45.81.42.208','2001-02-08 12:19:06'),
    (352,'Joe','jpalmer9r@phpbb.com','163.202.92.190','1970-01-05 11:29:12'),
    (353,'Sandra','slewis9s@dyndns.org','77.215.201.236','1974-01-05 07:04:04'),
    (354,'Todd','tfranklin9t@g.co','167.125.181.82','2009-09-28 10:13:58'),
    (355,'Joseph','jlewis9u@webmd.com','244.204.6.11','1990-10-21 15:49:57'),
    (356,'Alan','aknight9v@nydailynews.com','152.197.95.83','1996-03-08 08:43:17'),
    (357,'Sharon','sdean9w@123-reg.co.uk','237.46.40.26','1985-11-30 12:09:24'),
    (358,'Annie','awright9x@cafepress.com','190.45.231.111','2000-08-24 11:56:06'),
    (359,'Diane','dhamilton9y@youtube.com','85.146.171.196','2015-02-24 02:03:57'),
    (360,'Antonio','alane9z@auda.org.au','61.63.146.203','2001-05-13 03:43:34'),
    (361,'Matthew','mallena0@hhs.gov','29.97.32.19','1973-02-19 23:43:32'),
    (362,'Bonnie','bfowlera1@soup.io','251.216.99.53','2013-08-01 15:35:41'),
    (363,'Margaret','mgraya2@examiner.com','69.255.151.79','1998-01-23 22:24:59'),
    (364,'Joan','jwagnera3@printfriendly.com','192.166.120.61','1973-07-13 00:30:22'),
    (365,'Catherine','cperkinsa4@nytimes.com','58.21.24.214','2006-11-19 11:52:26'),
    (366,'Mark','mcartera5@cpanel.net','220.33.102.142','2007-09-09 09:43:27'),
    (367,'Paula','ppricea6@msn.com','36.182.238.124','2009-11-11 09:13:05'),
    (368,'Catherine','cgreena7@army.mil','228.203.58.19','2005-08-09 16:52:15'),
    (369,'Helen','hhamiltona8@symantec.com','155.56.194.99','2005-02-01 05:40:36'),
    (370,'Jane','jmeyera9@ezinearticles.com','133.244.113.213','2013-11-06 22:10:23'),
    (371,'Wanda','wevansaa@bloglovin.com','233.125.192.48','1994-12-26 23:43:42'),
    (372,'Mark','mmarshallab@tumblr.com','114.74.60.47','2016-09-29 18:03:01'),
    (373,'Andrew','amartinezac@google.cn','182.54.37.130','1976-06-06 17:04:17'),
    (374,'Helen','hmoralesad@e-recht24.de','42.45.4.123','1977-03-28 19:06:59'),
    (375,'Bonnie','bstoneae@php.net','196.149.79.137','1970-02-05 17:05:58'),
    (376,'Douglas','dfreemanaf@nasa.gov','215.65.124.218','2008-11-20 21:51:55'),
    (377,'Willie','wwestag@army.mil','35.189.92.118','1992-07-24 05:08:08'),
    (378,'Cheryl','cwagnerah@upenn.edu','228.239.222.141','2010-01-25 06:29:01'),
    (379,'Sandra','swardai@baidu.com','63.11.113.240','1985-05-23 08:07:37'),
    (380,'Julie','jrobinsonaj@jugem.jp','110.58.202.50','2015-03-05 09:42:07'),
    (381,'Larry','lwagnerak@shop-pro.jp','98.234.25.24','1975-07-22 22:22:02'),
    (382,'Juan','jcastilloal@yelp.com','24.174.74.202','2007-01-17 09:32:43'),
    (383,'Donna','dfrazieram@artisteer.com','205.26.147.45','1990-02-11 20:55:46'),
    (384,'Rachel','rfloresan@w3.org','109.60.216.162','1983-05-22 22:42:18'),
    (385,'Robert','rreynoldsao@theguardian.com','122.65.209.130','2009-05-01 18:02:51'),
    (386,'Donald','dbradleyap@etsy.com','42.54.35.126','1997-01-16 16:31:52'),
    (387,'Rachel','rfisheraq@nih.gov','160.243.250.45','2006-02-17 22:05:49'),
    (388,'Nicholas','nhamiltonar@princeton.edu','156.211.37.111','1976-06-21 03:36:29'),
    (389,'Timothy','twhiteas@ca.gov','36.128.23.70','1975-09-24 03:51:18'),
    (390,'Diana','dbradleyat@odnoklassniki.ru','44.102.120.184','1983-04-27 09:02:50'),
    (391,'Billy','bfowlerau@jimdo.com','91.200.68.196','1995-01-29 06:57:35'),
    (392,'Bruce','bandrewsav@ucoz.com','48.12.101.125','1992-10-27 04:31:39'),
    (393,'Linda','lromeroaw@usa.gov','100.71.233.19','1992-06-08 15:13:18'),
    (394,'Debra','dwatkinsax@ucoz.ru','52.160.233.193','2001-11-11 06:51:01'),
    (395,'Katherine','kburkeay@wix.com','151.156.242.141','2010-06-14 19:54:28'),
    (396,'Martha','mharrisonaz@youku.com','21.222.10.199','1989-10-16 14:17:55'),
    (397,'Dennis','dwellsb0@youtu.be','103.16.29.3','1985-12-21 06:05:51'),
    (398,'Gloria','grichardsb1@bloglines.com','90.147.120.234','1982-08-27 01:04:43'),
    (399,'Brenda','bfullerb2@t.co','33.253.63.90','2011-04-20 05:00:35'),
    (400,'Larry','lhendersonb3@disqus.com','88.95.132.128','1982-08-31 02:15:12'),
    (401,'Richard','rlarsonb4@wisc.edu','13.48.231.150','1979-04-15 14:08:09'),
    (402,'Terry','thuntb5@usa.gov','65.91.103.240','1998-05-15 11:50:49'),
    (403,'Harry','hburnsb6@nasa.gov','33.38.21.244','1981-04-12 14:02:20'),
    (404,'Diana','dellisb7@mlb.com','218.229.81.135','1997-01-29 00:17:25'),
    (405,'Jack','jburkeb8@tripadvisor.com','210.227.182.216','1984-03-09 17:24:03'),
    (406,'Julia','jlongb9@fotki.com','10.210.12.104','2005-10-26 03:54:13'),
    (407,'Lois','lscottba@msu.edu','188.79.136.138','1973-02-02 18:40:39'),
    (408,'Sandra','shendersonbb@shareasale.com','114.171.220.108','2012-06-09 18:22:26'),
    (409,'Irene','isanchezbc@cdbaby.com','109.255.50.119','1983-09-28 21:11:27'),
    (410,'Emily','ebrooksbd@bandcamp.com','227.81.93.79','1970-08-31 21:08:01'),
    (411,'Michelle','mdiazbe@businessweek.com','236.249.6.226','1993-05-22 08:07:07'),
    (412,'Tammy','tbennettbf@wisc.edu','145.253.239.152','1978-12-31 20:24:51'),
    (413,'Christine','cgreenebg@flickr.com','97.25.140.118','1978-07-17 12:55:30'),
    (414,'Patricia','pgarzabh@tuttocitta.it','139.246.192.211','1984-02-27 13:40:08'),
    (415,'Kimberly','kromerobi@aol.com','73.56.88.247','1976-09-16 14:22:04'),
    (416,'George','gjohnstonbj@fda.gov','240.36.245.185','1979-07-24 14:36:02'),
    (417,'Eugene','efullerbk@sciencedaily.com','42.38.105.140','2012-09-12 01:56:41'),
    (418,'Andrea','astevensbl@goo.gl','31.152.207.204','1979-05-24 11:06:21'),
    (419,'Shirley','sreidbm@scientificamerican.com','103.60.31.241','1984-02-23 04:07:41'),
    (420,'Terry','tmorenobn@blinklist.com','92.161.34.42','1994-06-25 14:01:35'),
    (421,'Christopher','cmorenobo@go.com','158.86.176.82','1973-09-05 09:18:47'),
    (422,'Dennis','dhansonbp@ning.com','40.160.81.75','1982-01-20 10:19:41'),
    (423,'Beverly','brussellbq@de.vu','138.32.56.204','1997-11-06 07:20:19'),
    (424,'Howard','hparkerbr@163.com','103.171.134.171','2015-06-24 15:37:10'),
    (425,'Helen','hmccoybs@fema.gov','61.200.4.71','1995-06-20 08:59:10'),
    (426,'Ann','ahudsonbt@cafepress.com','239.187.71.125','1977-04-11 07:59:28'),
    (427,'Tina','twestbu@nhs.uk','80.213.117.74','1992-08-19 05:54:44'),
    (428,'Terry','tnguyenbv@noaa.gov','21.93.118.95','1991-09-19 23:22:55'),
    (429,'Ashley','aburtonbw@wix.com','233.176.205.109','2009-11-10 05:01:20'),
    (430,'Eric','emyersbx@1und1.de','168.91.212.67','1987-08-10 07:16:20'),
    (431,'Barbara','blittleby@lycos.com','242.14.189.239','2008-08-02 12:13:04'),
    (432,'Sean','sevansbz@instagram.com','14.39.177.13','2007-04-16 17:28:49'),
    (433,'Shirley','sburtonc0@newsvine.com','34.107.138.76','1980-12-10 02:19:29'),
    (434,'Patricia','pfreemanc1@so-net.ne.jp','219.213.142.117','1987-03-01 02:25:45'),
    (435,'Paula','pfosterc2@vkontakte.ru','227.14.138.141','1972-09-22 12:59:34'),
    (436,'Nicole','nstewartc3@1688.com','8.164.23.115','1998-10-27 00:10:17'),
    (437,'Earl','ekimc4@ovh.net','100.26.244.177','2013-01-22 10:05:46'),
    (438,'Beverly','breedc5@reuters.com','174.12.226.27','1974-09-22 07:29:36'),
    (439,'Lawrence','lbutlerc6@a8.net','105.164.42.164','1992-06-05 00:43:40'),
    (440,'Charles','cmoorec7@ucoz.com','252.197.131.69','1990-04-09 02:34:05'),
    (441,'Alice','alawsonc8@live.com','183.73.220.232','1989-02-28 09:11:04'),
    (442,'Dorothy','dcarpenterc9@arstechnica.com','241.47.200.14','2005-05-02 19:57:21'),
    (443,'Carolyn','cfowlerca@go.com','213.109.55.202','1978-09-10 20:18:20'),
    (444,'Anthony','alongcb@free.fr','169.221.158.204','1984-09-13 01:59:23'),
    (445,'Annie','amoorecc@e-recht24.de','50.34.148.61','2009-03-26 03:41:07'),
    (446,'Carlos','candrewscd@ihg.com','236.69.59.212','1972-03-29 22:42:48'),
    (447,'Beverly','bramosce@google.ca','164.250.184.49','1982-11-10 04:34:01'),
    (448,'Teresa','tlongcf@umich.edu','174.88.53.223','1987-05-17 12:48:00'),
    (449,'Roy','rboydcg@uol.com.br','91.58.243.215','1974-06-16 17:59:54'),
    (450,'Ashley','afieldsch@tamu.edu','130.138.11.126','1983-09-15 05:52:36'),
    (451,'Judith','jhawkinsci@cmu.edu','200.187.103.245','2003-10-22 12:24:03'),
    (452,'Rebecca','rwestcj@ocn.ne.jp','72.85.3.103','1980-11-13 11:01:26'),
    (453,'Raymond','rporterck@infoseek.co.jp','146.33.216.151','1982-05-17 23:58:03'),
    (454,'Janet','jmarshallcl@odnoklassniki.ru','52.46.193.166','1998-10-04 00:02:21'),
    (455,'Shirley','speterscm@salon.com','248.126.31.15','1987-01-30 06:04:59'),
    (456,'Annie','abowmancn@economist.com','222.213.248.59','2006-03-14 23:52:59'),
    (457,'Jean','jlarsonco@blogspot.com','71.41.25.195','2007-09-08 23:49:45'),
    (458,'Phillip','pmoralescp@stanford.edu','74.119.87.28','2011-03-14 20:25:40'),
    (459,'Norma','nrobinsoncq@economist.com','28.225.21.54','1989-10-21 01:22:43'),
    (460,'Kimberly','kclarkcr@dion.ne.jp','149.171.132.153','2008-06-27 02:27:30'),
    (461,'Ruby','rmorriscs@ucla.edu','177.85.163.249','2016-01-28 16:43:44'),
    (462,'Jonathan','jcastilloct@tripod.com','78.4.28.77','2000-05-24 17:33:06'),
    (463,'Edward','ebryantcu@jigsy.com','140.31.98.193','1992-12-17 08:32:47'),
    (464,'Chris','chamiltoncv@eepurl.com','195.171.234.206','1970-12-05 03:42:19'),
    (465,'Michael','mweavercw@reference.com','7.233.133.213','1987-03-29 02:30:54'),
    (466,'Howard','hlawrencecx@businessweek.com','113.225.124.224','1990-07-30 07:20:57'),
    (467,'Philip','phowardcy@comsenz.com','159.170.247.249','2010-10-15 10:18:37'),
    (468,'Mary','mmarshallcz@xing.com','125.132.189.70','2007-07-19 13:48:47'),
    (469,'Scott','salvarezd0@theguardian.com','78.49.103.230','1987-10-31 06:10:44'),
    (470,'Wayne','wcarrolld1@blog.com','238.1.120.204','1980-11-19 03:26:10'),
    (471,'Jennifer','jwoodsd2@multiply.com','92.20.224.49','2010-05-06 22:17:04'),
    (472,'Raymond','rwelchd3@toplist.cz','176.158.35.240','2007-12-12 19:02:51'),
    (473,'Steven','sdixond4@wisc.edu','167.55.237.52','1984-05-05 11:44:37'),
    (474,'Ralph','rjamesd5@ameblo.jp','241.190.50.133','2000-07-06 08:44:37'),
    (475,'Jason','jrobinsond6@hexun.com','138.119.139.56','2006-02-03 05:27:45'),
    (476,'Doris','dwoodd7@fema.gov','180.220.156.190','1978-05-11 20:14:20'),
    (477,'Elizabeth','eberryd8@youtu.be','74.188.53.229','2006-11-18 08:29:06'),
    (478,'Irene','igilbertd9@privacy.gov.au','194.152.218.1','1985-09-17 02:46:52'),
    (479,'Jessica','jdeanda@ameblo.jp','178.103.93.118','1974-06-07 19:04:05'),
    (480,'Rachel','ralvarezdb@phoca.cz','17.22.223.174','1999-03-08 02:43:25'),
    (481,'Kenneth','kthompsondc@shinystat.com','229.119.91.234','2007-05-15 13:17:32'),
    (482,'Harold','hmurraydd@parallels.com','133.26.188.80','1993-11-15 03:42:07'),
    (483,'Paula','phowellde@samsung.com','34.215.28.216','1993-11-29 15:55:00'),
    (484,'Ruth','rpiercedf@tripadvisor.com','111.30.130.123','1986-08-17 10:19:38'),
    (485,'Phyllis','paustindg@vk.com','50.84.34.178','1994-04-13 03:05:24'),
    (486,'Laura','lfosterdh@usnews.com','37.8.101.33','2001-06-30 08:58:59'),
    (487,'Eric','etaylordi@com.com','103.183.253.45','2006-09-15 20:18:46'),
    (488,'Doris','driveradj@prweb.com','247.16.2.199','1989-05-08 09:27:09'),
    (489,'Ryan','rhughesdk@elegantthemes.com','103.234.153.232','1989-08-01 18:36:06'),
    (490,'Steve','smoralesdl@jigsy.com','3.76.84.207','2011-03-13 17:01:05'),
    (491,'Louis','lsullivandm@who.int','78.135.44.208','1975-11-26 16:01:23'),
    (492,'Catherine','ctuckerdn@seattletimes.com','93.137.106.21','1990-03-13 16:14:56'),
    (493,'Ann','adixondo@gmpg.org','191.136.222.111','2002-06-05 14:22:18'),
    (494,'Johnny','jhartdp@amazon.com','103.252.198.39','1988-07-30 23:54:49'),
    (495,'Susan','srichardsdq@skype.com','126.247.192.11','2005-01-09 12:08:14'),
    (496,'Brenda','bparkerdr@skype.com','63.232.216.86','1974-05-18 05:58:29'),
    (497,'Tammy','tmurphyds@constantcontact.com','56.56.37.112','2014-08-05 18:22:25'),
    (498,'Larry','lhayesdt@wordpress.com','162.146.13.46','1997-02-26 14:01:53'),
    (499,NULL,'ethomasdu@hhs.gov','6.241.88.250','2007-09-14 13:03:34'),
    (500,'Paula','pshawdv@networksolutions.com','123.27.47.249','2003-10-30 21:19:20');
"""


class SeedConfigBase(object):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "seeds": {
                "quote_columns": False,
            },
        }


class SeedTestBase(SeedConfigBase):
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        """Create table for ensuring seeds and models used in tests build correctly"""
        project.run_sql(seeds__expected_sql)

    @pytest.fixture(scope="class")
    def seeds(self, test_data_dir):
        return {"seed_actual.csv": seed__actual_csv}

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "models__downstream_from_seed_actual.sql": models__downstream_from_seed_actual,
        }

    def _build_relations_for_test(self, project):
        """The testing environment needs seeds and models to interact with"""
        seed_result = run_dbt(["seed"])
        assert len(seed_result) == 1
        check_relations_equal(project.adapter, ["seed_expected", "seed_actual"])

        run_result = run_dbt()
        assert len(run_result) == 1
        check_relations_equal(
            project.adapter, ["models__downstream_from_seed_actual", "seed_expected"]
        )

    def _check_relation_end_state(self, run_result, project, exists: bool):
        assert len(run_result) == 1
        check_relations_equal(project.adapter, ["seed_actual", "seed_expected"])
        if exists:
            check_table_does_exist(project.adapter, "models__downstream_from_seed_actual")
        else:
            check_table_does_not_exist(project.adapter, "models__downstream_from_seed_actual")


class TestBasicSeedTests(SeedTestBase):
    def test_simple_seed(self, project):
        """Build models and observe that run truncates a seed and re-inserts rows"""
        self._build_relations_for_test(project)
        self._check_relation_end_state(run_result=run_dbt(["seed"]), project=project, exists=True)

    def test_simple_seed_full_refresh_flag(self, project):
        """Drop the seed_actual table and re-create. Verifies correct behavior by the absence of the
        model which depends on seed_actual."""
        self._build_relations_for_test(project)
        self._check_relation_end_state(
            run_result=run_dbt(["seed", "--full-refresh"]), project=project, exists=True
        )


class TestSeedConfigFullRefreshOn(SeedTestBase):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "seeds": {"quote_columns": False, "full_refresh": True},
        }

    def test_simple_seed_full_refresh_config(self, project):
        """config option should drop current model and cascade drop to downstream models"""
        self._build_relations_for_test(project)
        self._check_relation_end_state(run_result=run_dbt(["seed"]), project=project, exists=True)


class TestSeedConfigFullRefreshOff(SeedTestBase):
    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "seeds": {"quote_columns": False, "full_refresh": False},
        }

    def test_simple_seed_full_refresh_config(self, project):
        """Config options should override a full-refresh flag because config is higher priority"""
        self._build_relations_for_test(project)
        self._check_relation_end_state(run_result=run_dbt(["seed"]), project=project, exists=True)
        self._check_relation_end_state(
            run_result=run_dbt(["seed", "--full-refresh"]), project=project, exists=True
        )


class TestSeedCustomSchema(SeedTestBase):
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        """Create table for ensuring seeds and models used in tests build correctly"""
        project.run_sql(seeds__expected_sql)

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "seeds": {
                "schema": "custom_schema",
                "quote_columns": False,
            },
        }

    def test_simple_seed_with_schema(self, project):
        seed_results = run_dbt(["seed"])
        assert len(seed_results) == 1
        custom_schema = f"{project.test_schema}_custom_schema"
        check_relations_equal(project.adapter, [f"{custom_schema}.seed_actual", "seed_expected"])

        # this should truncate the seed_actual table, then re-insert
        results = run_dbt(["seed"])
        assert len(results) == 1
        custom_schema = f"{project.test_schema}_custom_schema"
        check_relations_equal(project.adapter, [f"{custom_schema}.seed_actual", "seed_expected"])

    def test_simple_seed_with_drop_and_schema(self, project):
        seed_results = run_dbt(["seed"])
        assert len(seed_results) == 1
        custom_schema = f"{project.test_schema}_custom_schema"
        check_relations_equal(project.adapter, [f"{custom_schema}.seed_actual", "seed_expected"])

        # this should drop the seed table, then re-create
        results = run_dbt(["seed", "--full-refresh"])
        assert len(results) == 1
        custom_schema = f"{project.test_schema}_custom_schema"
        check_relations_equal(project.adapter, [f"{custom_schema}.seed_actual", "seed_expected"])


@pytest.mark.skip(reason="Cascade is not supported in Drop Schema")
class TestSimpleSeedEnabledViaConfig(object):
    @pytest.fixture(scope="session")
    def seeds(self):
        return {
            "seed_enabled.csv": seeds__enabled_in_config_csv,
            "seed_disabled.csv": seeds__disabled_in_config_csv,
            "seed_tricky.csv": seeds__tricky_csv,
        }

    @pytest.fixture(scope="class")
    def project_config_update(self):
        return {
            "seeds": {
                "test": {"seed_enabled": {"enabled": True}, "seed_disabled": {"enabled": False}},
                "quote_columns": False,
            },
        }

    @pytest.fixture(scope="function")
    def clear_test_schema(self, project):
        yield
        project.run_sql(f"drop schema if exists {project.test_schema}")

    def test_simple_seed_with_disabled(self, clear_test_schema, project):
        results = run_dbt(["seed"])
        assert len(results) == 2
        check_table_does_exist(project.adapter, "seed_enabled")
        check_table_does_not_exist(project.adapter, "seed_disabled")
        check_table_does_exist(project.adapter, "seed_tricky")

    def test_simple_seed_selection(self, clear_test_schema, project):
        results = run_dbt(["seed", "--select", "seed_enabled"])
        assert len(results) == 1
        check_table_does_exist(project.adapter, "seed_enabled")
        check_table_does_not_exist(project.adapter, "seed_disabled")
        check_table_does_not_exist(project.adapter, "seed_tricky")

    def test_simple_seed_exclude(self, clear_test_schema, project):
        results = run_dbt(["seed", "--exclude", "seed_enabled"])
        assert len(results) == 1
        check_table_does_not_exist(project.adapter, "seed_enabled")
        check_table_does_not_exist(project.adapter, "seed_disabled")
        check_table_does_exist(project.adapter, "seed_tricky")


class TestSeedParsing(SeedConfigBase):
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        """Create table for ensuring seeds and models used in tests build correctly"""
        project.run_sql(seeds__expected_sql)

    @pytest.fixture(scope="class")
    def seeds(self):
        return {"seed.csv": seeds__wont_parse_csv}

    @pytest.fixture(scope="class")
    def models(self):
        return {"model.sql": models__from_basic_seed}

    def test_dbt_run_skips_seeds(self, project):
        # run does not try to parse the seed files
        assert len(run_dbt()) == 1

        # make sure 'dbt seed' fails, otherwise our test is invalid!
        run_dbt(["seed"], expect_pass=False)


class TestSimpleSeedWithBOM(SeedConfigBase):
    # Reference: BOM = byte order mark; see https://www.ibm.com/docs/en/netezza?topic=formats-byte-order-mark
    # Tests for hidden unicode character in csv
    @pytest.fixture(scope="class", autouse=True)
    def setUp(self, project):
        """Create table for ensuring seeds and models used in tests build correctly"""
        project.run_sql(seeds__expected_sql)
        copy_file(
            project.test_dir,
            "seed_bom.csv",
            project.project_root / Path("seeds") / "seed_bom.csv",
            "",
        )

    def test_simple_seed(self, project):
        seed_result = run_dbt(["seed"])
        assert len(seed_result) == 1
        # encoding param must be specified in open, so long as Python reads files with a
        # default file encoding for character sets beyond extended ASCII.
        with open(
            project.project_root / Path("seeds") / Path("seed_bom.csv"), encoding="utf-8"
        ) as fp:
            assert fp.read(1) == BOM_UTF8.decode("utf-8")
        check_relations_equal(project.adapter, ["seed_expected", "seed_bom"])


class TestSeedSpecificFormats(SeedConfigBase):
    """Expect all edge cases to build"""

    @staticmethod
    def _make_big_seed(test_data_dir):
        mkdir(test_data_dir)
        big_seed_path = test_data_dir / Path("tmp.csv")
        with open(big_seed_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["seed_id"])
            for i in range(0, 20000):
                writer.writerow([i])
        return big_seed_path

    @pytest.fixture(scope="class")
    def seeds(self, test_data_dir):
        big_seed_path = self._make_big_seed(test_data_dir)
        big_seed = read_file(big_seed_path)

        yield {
            "big_seed.csv": big_seed,
            "seed.with.dots.csv": seed__with_dots_csv,
            "seed_unicode.csv": seed__unicode_csv,
        }
        rm_dir(test_data_dir)

    def test_simple_seed(self, project):
        results = run_dbt(["seed"])
        assert len(results) == 3
