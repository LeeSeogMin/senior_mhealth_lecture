import 'package:flutter/foundation.dart';

/// Log level enumeration following Dart style guide
enum LogLevel {
  verbose(0),
  debug(1),
  info(2),
  warning(3),
  error(4);

  const LogLevel(this.value);
  final int value;
}

/// A simple logging service that doesn't require external dependencies.
/// This can be replaced with a more robust solution like the logging package when available.
class LogService {
  // Current minimum log level
  static LogLevel _minLevel = kDebugMode ? LogLevel.verbose : LogLevel.info;

  /// Set the minimum log level
  static void setLogLevel(LogLevel level) {
    _minLevel = level;
  }

  /// Log a verbose message
  static void verbose(String tag, String message) {
    if (_minLevel.value <= LogLevel.verbose.value) {
      debugPrint('VERBOSE/$tag: $message');
    }
  }

  /// Log a debug message
  static void debug(String tag, String message) {
    if (_minLevel.value <= LogLevel.debug.value) {
      debugPrint('DEBUG/$tag: $message');
    }
  }

  /// Log an info message
  static void info(String tag, String message) {
    if (_minLevel.value <= LogLevel.info.value) {
      debugPrint('INFO/$tag: $message');
    }
  }

  /// Log a warning message
  static void warning(String tag, String message) {
    if (_minLevel.value <= LogLevel.warning.value) {
      debugPrint('WARNING/$tag: $message');
    }
  }

  /// Log an error message
  static void error(String tag, String message) {
    if (_minLevel.value <= LogLevel.error.value) {
      debugPrint('ERROR/$tag: $message');
    }
  }
}
