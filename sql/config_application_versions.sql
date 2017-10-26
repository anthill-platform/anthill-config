CREATE TABLE `config_application_versions` (
  `gamespace_id` int(11) unsigned NOT NULL,
  `application_name` varchar(64) NOT NULL DEFAULT '',
  `application_version` varchar(64) NOT NULL DEFAULT '',
  `build_id` int(11) unsigned NOT NULL,
  PRIMARY KEY (`gamespace_id`,`application_name`,`application_version`),
  KEY `build_id` (`build_id`),
  KEY `application_name` (`application_name`,`application_version`),
  CONSTRAINT `config_application_versions_ibfk_1` FOREIGN KEY (`build_id`) REFERENCES `config_builds` (`build_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;