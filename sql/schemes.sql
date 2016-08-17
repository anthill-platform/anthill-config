CREATE TABLE `schemes` (
  `scheme_id` int(11) NOT NULL AUTO_INCREMENT,
  `gamespace_id` int(10) unsigned NOT NULL,
  `application_name` varchar(45) NOT NULL,
  `application_version` varchar(45) NOT NULL DEFAULT '',
  `payload` json NOT NULL,
  PRIMARY KEY (`scheme_id`),
  UNIQUE KEY `gamespace_id` (`gamespace_id`,`application_name`,`application_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;