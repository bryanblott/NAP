
###############################################################################
# This module provides a simple logging utility function to print messages 
# with a specified severity level.
#
# Parameters:
# message (str): The message to log.
# level (str): The severity level of the message. Default is "INFO".
#
# Returns:
# None
###############################################################################


################################################################################
# Code
################################################################################
def log(message, level="INFO"):
    print(f"[{level}] {message}")
