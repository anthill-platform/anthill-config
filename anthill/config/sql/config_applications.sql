CREATE TABLE `config_applications` (
  `application_name` varchar(255) NOT NULL DEFAULT '',
  `gamespace_id` int(10) unsigned NOT NULL,
  `deployment_method` varchar(64) NOT NULL DEFAULT '',
  `deployment_data` json NOT NULL,
  `default_build` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`gamespace_id`,`application_name`),
  UNIQUE KEY `application_name` (`application_name`,`gamespace_id`),
  KEY `default_build` (`default_build`),
  CONSTRAINT `config_applications_ibfk_1` FOREIGN KEY (`default_build`) REFERENCES `config_builds` (`build_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;