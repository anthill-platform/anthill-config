CREATE TABLE `config_builds` (
  `build_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `gamespace_id` int(11) unsigned NOT NULL,
  `application_name` varchar(64) NOT NULL DEFAULT '',
  `build_url` varchar(255) DEFAULT NULL,
  `build_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `build_comment` varchar(255) NOT NULL DEFAULT '',
  `build_author` int(10) unsigned NOT NULL,
  PRIMARY KEY (`build_id`),
  KEY `gamespace_id` (`gamespace_id`,`application_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;