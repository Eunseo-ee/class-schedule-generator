CREATE TABLE course (
  id            BIGINT       NOT NULL AUTO_INCREMENT,
  academic_year SMALLINT     NOT NULL,
  semester      TINYINT      NOT NULL,
  subj_cd       VARCHAR(10)  NOT NULL,
  lect_numb     VARCHAR(10)  NOT NULL,
  name          VARCHAR(200) NOT NULL,
  professor     VARCHAR(200) NULL,
  credits       TINYINT UNSIGNED NOT NULL,
  category      VARCHAR(10)  NOT NULL,
  department    VARCHAR(100) NOT NULL,
  capacity      SMALLINT UNSIGNED NOT NULL,
  room          VARCHAR(255) NULL,
  day_night     VARCHAR(10)  NOT NULL,
  language      VARCHAR(20)  NOT NULL,
  note          TEXT         NULL,
  time_raw      VARCHAR(255) NULL,
  time_status   VARCHAR(20)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_course_lecture (academic_year, semester, subj_cd, lect_numb)
);

CREATE TABLE course_time_slot (
  id          BIGINT NOT NULL AUTO_INCREMENT,
  course_id   BIGINT NOT NULL,
  day_of_week VARCHAR(3) NOT NULL,
  start_slot  TINYINT UNSIGNED NOT NULL,
  end_slot    TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_slot (course_id, day_of_week, start_slot),
  CONSTRAINT fk_slot_course FOREIGN KEY (course_id)
    REFERENCES course (id) ON DELETE CASCADE,
  CONSTRAINT ck_slot_day CHECK (day_of_week IN ('MON','TUE','WED','THU','FRI','SAT','SUN')),
  CONSTRAINT ck_slot_range CHECK (start_slot < end_slot)
);