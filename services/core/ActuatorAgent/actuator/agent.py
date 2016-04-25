# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2015, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
# official policies, either expressed or implied, of the FreeBSD
# Project.
#
# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization that
# has cooperated in the development of these materials, makes any
# warranty, express or implied, or assumes any legal liability or
# responsibility for the accuracy, completeness, or usefulness or any
# information, apparatus, product, software, or process disclosed, or
# represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does not
# necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830

# }}}

"""
.. _actuator-agent:

The Actuator Agent is used to manage write access to devices. Agents
may request scheduled times, called Tasks, to interact with one or more
devices.

The interactions with the ActuatorAgent are handled via a pub/sub or RPC
interface provided by the message bus. 

It is recommended RPC be used for interacting with the ActuatorAgent.

The pub/sub interface is primarily for VOLTTRON 2.0 agents. 

The Actuator Agent also triggers the heart beat on devices whose 
drivers are configured to do so. 

ActuatorAgent Configuration
===========================

    "schedule_publish_interval"
        Interval between published schedule announcements in seconds. Defaults to 30. See `Schedule State Publishes`_.
    "preempt_grace_time"
        Minimum time given to Tasks which have been preempted to clean up in seconds. Defaults to 60.
    "schedule_state_file"
        File used to save and restore Task states if the ActuatorAgent restarts for any reason. File will be
        created if it does not exist when it is needed.
    "heartbeat_period"
        The frequency to send heartbeat signal to devices. Defaults to 60.
        

Sample configuration file
-------------------------

.. code-block:: python

    {
        "schedule_publish_interval": 30,
        "schedule_state_file": "actuator_state.pickle"
    }

Workflow
========

Interacting with the Actuator Agent follows a basic steps:

- Schedule one or more blocks of time with one or more devices. This is called a Task.
- If needed wait until a block of time starts.
- Set one or more values on the reserved devices.
- Cancel the schedule when finished.

Scheduling a New Task
=====================

:py:meth:`RPC interface <ActuatorAgent.request_new_schedule>` 
:py:meth:`PUB/SUB interface <ActuatorAgent.handle_schedule_request>` 

Creating a Task requires four things:

- The requester of the Task. This is the Agent's ID.
- A name for the Task.
- The Task's priority.
- A list of devices and time ranges for each device.


Task Priority
---------------

There are three valid prioirity levels:

    "HIGH"
        This Task cannot be preempted under any circumstance. 
        This Task may preempt other conflicting preemptable Tasks.
    "LOW"
        This Task cannot be preempted **once it has started**. 
        A Task is considered started once the earliest time slot on any 
        device has been reached. This Task may not preempt other Tasks.
    "LOW_PREEMPT"
        This Task may be preempted at any time. 
        If the Task is preempted once it has begun running any current 
        time slots will be given a grace period (configurable in the 
        ActuatorAgent configuration file, defaults to 60 seconds) before 
        being revoked. This Task may not preempt other Tasks.
        
Whenever a Task is preempted the Actuator Agent will publish a message to 
``devices/actuators/schedule/result`` indicating that the Task has
been cancelled due to being preempted. See `Preemption Publishes`_

Even when using the RPC interface agents which schedule low priority tasks
may need to subscribe to ``devices/actuators/schedule/result`` to learn when
its Tasks are canceled due to preemption.

Device Schedule
----------------

The device schedule is a list of block of time for each device.

Both the RPC and PUB/SUB interface accept schedules in the following
format:

.. code-block:: python

    [
        ["campus/building/device1", #First time slot.
         "2013-12-06 16:00:00",     #Start of time slot.
         "2013-12-06 16:20:00"],    #End of time slot.
        ["campus/building/device1", #Second time slot.
         "2013-12-06 18:00:00",     #Start of time slot.
         "2013-12-06 18:20:00"],    #End of time slot.
        ["campus/building/device2", #Third time slot.
         "2013-12-06 16:00:00",     #Start of time slot.
         "2013-12-06 16:20:00"],    #End of time slot.
        #etc...
    ]
    
.. note:: 

    Points on Task Scheduling
    
    -  Task id and requester id (agentid) should be a non empty value of
       type string
    -  A Task schedule must have at least one time slot.
    -  The start and end times are parsed with `dateutil's date/time
       parser <http://labix.org/python-dateutil#head-c0e81a473b647dfa787dc11e8c69557ec2c3ecd2>`__.
       **The default string representation of a python datetime object will
       parse without issue.**
    -  Two Tasks are considered conflicted if at least one time slot on a
       device from one task overlaps the time slot of the other on the same
       device.
    -  The end time of one time slot can be the same as the start time of
       another time slot for the same device. This will not be considered a
       conflict. For example, time\_slot1(device0, time1, **time2**) and
       time\_slot2(device0,\ **time2**, time3) are not considered a conflict
    -  A request must not conflict with itself.
    
New Task Response
-----------------

Both the RPC and PUB/SUB interface respond to requests with the result
in the following format:

.. code-block:: python

    {
        'result': <'SUCCESS', 'FAILURE'>,
        'info': <Failure reason string, if any>,
        'data': <Data about the failure or cancellation, if any>
    }
    
The PUB/SUB interface will respond to requests on the
``devices/actuators/schedule/result`` topic.

The PUB/SUB interface responses will have the following header:

.. code-block:: python

    {
        'type': 'NEW_SCHEDULE'
        'requesterID': <Agent ID from the request>,
        'taskID': <Task ID from the request>
    }
    
Failure Reasons
***************

In many cases the ActuatorAgent will try to give good feedback as to why
a request failed. The type of failure will populate "info" item as a 
string.


Some of these errors only apply to the PUB/SUB interface.

General Failures
^^^^^^^^^^^^^^^^

"INVALID_REQUEST_TYPE"
    Request type was not "NEW_SCHEDULE" or "CANCEL_SCHEDULE".
"MISSING_TASK_ID"
    Failed to supply a taskID.
"MISSING_AGENT_ID"
    AgentID not supplied.

Task Schedule Failures
^^^^^^^^^^^^^^^^^^^^^^

"TASK_ID_ALREADY_EXISTS "
    The supplied taskID already belongs to an existing task.
"MISSING_PRIORITY"
    Failed to supply a priority for a Task schedule request.
"INVALID_PRIORITY"
    Priority not one of "HIGH", "LOW", or "LOW_PREEMPT".
"MALFORMED_REQUEST_EMPTY"
    Request list is missing or empty.
"REQUEST_CONFLICTS_WITH_SELF"
    Requested time slots on the same device overlap.
"MALFORMED_REQUEST"
    Reported when the request parser raises an unhandled exception. 
    The exception name and info are appended to this info string.
"CONFLICTS_WITH_EXISTING_SCHEDULES"
    This schedule conflict with an existing schedules that it cannot 
    preempt. The data item for the results will contain info about 
    the conflicts in this form:

    .. code-block:: python
    
        {
            '<agentID1>': 
            {
                '<taskID1>':
                [
                    ["campus/building/device1", 
                     "2013-12-06 16:00:00",     
                     "2013-12-06 16:20:00"],
                    ["campus/building/device1", 
                     "2013-12-06 18:00:00",     
                     "2013-12-06 18:20:00"]     
                ]
                '<taskID2>':[...]
            }
            '<agentID2>': {...}
        }

Device Interaction
==================

Getting values
--------------

:py:meth:`RPC interface <ActuatorAgent.get_point>` 
:py:meth:`PUB/SUB interface <ActuatorAgent.handle_get>` 

While a device driver for a device will periodically broadcast 
the state of a device you may want an up to the moment value for 
point on a device.

As of VOLTTRON 3.5 it is no longer required to have the device 
scheduled before you can use this interface.

Setting Values
--------------

:py:meth:`RPC interface <ActuatorAgent.set_point>` 
:py:meth:`PUB/SUB interface <ActuatorAgent.handle_set>` 

Failure to schedule the device first will result in an error.

Errors Setting Values
*********************

If there is an error the RPC interface will raise an exception 
and the PUB/SUB interface will publish to 

    ``devices/actuators/error/<full device path>/<actuation point>``

The headder of the publish will take this form: 

.. code-block:: python

    {
        'requesterID': <Agent ID>
    }
    
and a message body in this form:

.. code-block:: python

    {
        'type': <Class name of the exception raised by the request>
        'value': <Specific info about the error>
    }
    
Common Error Types
******************

    ``LockError``
        Raised when a request is made when we do not have permission to 
        use a device. (Forgot to schedule, preempted and we did not handle 
        the preemption message correctly, ran out of time in time slot, etc...)
    ``ValueError``
        Message missing (PUB/SUB only) or is the wrong data type. 

Most other error types involve problems with communication between the
VOLTTRON device drivers and the device itself.   

Reverting Values and Devices to a Default State
-----------------------------------------------

As of VOLTTRON 3.5 device drivers are now required to support
reverting to a default state. The exact mechanism used to 
accomplish this is driver specific.

Failure to schedule the device first will result in a ``LockError``.

:py:meth:`RPC revert value interface <ActuatorAgent.revert_point>`
:py:meth:`PUB/SUB revert value interface <ActuatorAgent.handle_revert_point>`

:py:meth:`RPC revert device interface <ActuatorAgent.revert_device>`
:py:meth:`PUB/SUB revert device interface <ActuatorAgent.handle_revert_device>`
        
Canceling a Task
================

:py:meth:`RPC interface <ActuatorAgent.request_cancel_schedule>` 
:py:meth:`PUB/SUB interface <ActuatorAgent.handle_schedule_request>` 

Cancelling a Task requires two things:

- The original requester of the Task. This is the Agent's ID.
- The name of the Task.

Cancel Task Response
--------------------

Both the RPC and PUB/SUB interface respond to requests with the result
in the following format:
            
.. code-block:: python

    {
        'result': <'SUCCESS', 'FAILURE'>,
        'info': <Failure reason, if any>,
        'data': {}
    }

.. note:: 
    There are some things to be aware of when canceling a schedule:
    
        - The requesterID and taskID must match the original values from the original request header.
        - After a Tasks time has passed there is no need to cancel it. Doing so will result in a "TASK_ID_DOES_NOT_EXIST" error.
        

If an attempt cancel a schedule fails than the "info" item will have any of the
following values:

    "TASK_ID_DOES_NOT_EXIST"
        Trying to cancel a Task which does not exist. This error can also occur when trying to cancel a finished Task.
    "AGENT_ID_TASK_ID_MISMATCH"
        A different agent ID is being used when trying to cancel a Task.

    
Preemption Publishes
====================

If a Task is preempted it will publish the following to the 
``devices/actuators/schedule/result`` topic:

.. code-block:: python

    {
        'result': 'PREEMPTED',
        'info': None,
        'data': {
                    'agentID': <Agent ID of preempting task>,
                    'taskID': <Task ID of preempting task>
                }
    }
    
Along with the following header:

.. code-block:: python

    {
        'type': 'CANCEL_SCHEDULE',
        'requesterID': <Agent ID associated with the preempted Task>,
        'taskID': <Task ID of the preempted Task>
    }
    
.. note::

    Remember that if your "LOW_PREEMPT" Task has already started and 
    is preempted you have a grace period to do any clean up before
    losing access to the device.
 
Schedule State Publishes
========================

Periodically the ActuatorAgent will publish the state of all currently
reserved devices. The first publish for a device will happen exactly
when the reserved block of time for a device starts.

For each device the ActuatorAgent will publish to an associated topic:

    ``devices/actuators/schedule/announce/<full device path>``

With the following header:

.. code-block:: python

    {
        'requesterID': <Agent with access>,
        'taskID': <Task associated with the time slot>
        'window': <Seconds remaining in the time slot>
    }

The frequency of the updates is configurable with the
"schedule_publish_interval" setting in the configuration.
"""

__docformat__ = 'reStructuredText'


import datetime
import sys
import logging

from volttron.platform.vip.agent import Agent, Core, RPC, Unreachable, compat
from volttron.platform.messaging import topics
from volttron.platform.agent import utils
from volttron.platform.messaging.utils import normtopic
from actuator.scheduler import ScheduleManager

from volttron.platform.jsonrpc import RemoteError

from dateutil.parser import parse

VALUE_RESPONSE_PREFIX = topics.ACTUATOR_VALUE()
REVERT_POINT_RESPONSE_PREFIX = topics.ACTUATOR_REVERTED_POINT()
REVERT_DEVICE_RESPONSE_PREFIX = topics.ACTUATOR_REVERTED_DEVICE()
ERROR_RESPONSE_PREFIX = topics.ACTUATOR_ERROR()

WRITE_ATTEMPT_PREFIX = topics.ACTUATOR_WRITE()

SCHEDULE_ACTION_NEW = 'NEW_SCHEDULE'
SCHEDULE_ACTION_CANCEL = 'CANCEL_SCHEDULE'

SCHEDULE_RESPONSE_SUCCESS = 'SUCCESS'
SCHEDULE_RESPONSE_FAILURE = 'FAILURE'

SCHEDULE_CANCEL_PREEMPTED = 'PREEMPTED'

ACTUATOR_COLLECTION = 'actuators'

utils.setup_logging()
_log = logging.getLogger(__name__)

__version__ = "0.3"

class LockError(StandardError):
    """Error raised when the user does not have a device scheuled
    and tries to use methods that require exclusive access."""
    pass


def actuator_agent(config_path, **kwargs):
    """Parses the Actuator Agent configuration and returns an instance of 
    the agent created using that configuation.
    
    :param config_path: Path to a configuation file. 
    
    :type config_path: str
    :returns: Actuator Agent
    :rtype: ActuatorAgent
    """
    config = utils.load_config(config_path)
    heartbeat_interval = int(config.get('heartbeat_period', 60))
    schedule_publish_interval = int(config.get('schedule_publish_interval', 60))
    schedule_state_file = config.get('schedule_state_file')
    preempt_grace_time = config.get('preempt_grace_time', 60)
    driver_vip_identity = config.get('driver_vip_identity', 'platform.driver')
    vip_identity = config.get('vip_identity', 'platform.actuator')
    # This agent needs to be named platform.actuator. Pop the uuid id off the kwargs
    kwargs.pop('identity', None)

    return ActuatorAgent(heartbeat_interval, schedule_publish_interval, 
                         schedule_state_file, preempt_grace_time,
                         driver_vip_identity, identity=vip_identity, **kwargs)

class ActuatorAgent(Agent):
    """
    The Actuator Agent regulates control of devices by other agents. Agents
    request a schedule and then issue commands to the device through
    this agent.
    
    The Actuator Agent also sends out the signal to drivers to trigger
    a device heartbeat.
    
    :param heartbeat_interval: Interval in seonds to send out a heartbeat 
        to devices. 
    :param schedule_publish_interval: Interval in seonds to publish the
        currently active schedules. 
    :param schedule_state_file: Name of the file to save the current schedule
        state to. This file is updated every time a schedule changes. 
    :param preempt_grace_time: Time in seconds after a schedule is preemted
        before it is actually cancelled. 
    :param driver_vip_identity: VIP identity of the Master Driver Agent. 

    :type heartbeat_interval: float
    :type schedule_publish_interval: float
    :type preempt_grace_time: float
    :type schedule_state_file: str
    :type driver_vip_identity: str
    """
    def __init__(self, heartbeat_interval=60, schedule_publish_interval=60,
                 schedule_state_file=None, preempt_grace_time=60,
                 driver_vip_identity='platform.driver', **kwargs):
        
        super(ActuatorAgent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self._update_event = None
        self._device_states = {}
        self.heartbeat_interval = heartbeat_interval
        self.schedule_publish_interval = schedule_publish_interval
        self.schedule_state_file = schedule_state_file
        self.preempt_grace_time = preempt_grace_time
        self.driver_vip_identity = driver_vip_identity
                
    def _heart_beat(self):
        _log.debug("sending heartbeat")
        try:
            self.vip.rpc.call(self.driver_vip_identity, 'heart_beat').get()
        except Unreachable:
            _log.warning("Master driver is not running")
        except Exception as e:
            _log.warning(''.join([e.__class__.__name__,'(',e.message,')']))

    @Core.receiver('onstart')
    def _on_start(self, sender, **kwargs):
        self._setup_schedule()
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topics.ACTUATOR_GET(),
                                  callback=self.handle_get)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topics.ACTUATOR_SET(),
                                  callback=self.handle_set)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topics.ACTUATOR_SCHEDULE_REQUEST(),
                                  callback=self.handle_schedule_request)
        
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topics.ACTUATOR_REVERT_POINT(),
                                  callback=self.handle_revert_point)
        
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topics.ACTUATOR_REVERT_DEVICE(),
                                  callback=self.handle_revert_device)
        
        self.core.periodic(self.heartbeat_interval, self._heart_beat)

    def _setup_schedule(self):
        now = datetime.datetime.now()
        self._schedule_manager = ScheduleManager(self.preempt_grace_time, now=now,
                                                 state_file_name=self.schedule_state_file)

        self._update_device_state_and_schedule(now)

    def _update_device_state_and_schedule(self, now):
        _log.debug("_update_device_state_and_schedule")
        # Sanity check now.
        # This is specifically for when this is running in a VM that gets suspeded and then resumed.
        # If we don't make this check a resumed VM will publish one event per minute of
        # time the VM was suspended for. 
        test_now = datetime.datetime.now()
        if test_now - now > datetime.timedelta(minutes=3):
            now = test_now

        self._device_states = self._schedule_manager.get_schedule_state(now)
        schedule_next_event_time = self._schedule_manager.get_next_event_time(now)
        new_update_event_time = self._get_ajusted_next_event_time(now, schedule_next_event_time)

        for device, state in self._device_states.iteritems():
            header = self._get_headers(state.agent_id, time=utils.format_timestamp(now), task_id=state.task_id)
            header['window'] = state.time_remaining
            topic = topics.ACTUATOR_SCHEDULE_ANNOUNCE_RAW.replace('{device}', device)
            self.vip.pubsub.publish('pubsub', topic, headers=header)

        if self._update_event is not None:
            # This won't hurt anything if we are canceling ourselves.
            self._update_event.cancel()
        self._update_event = self.core.schedule(new_update_event_time,
                                                self._update_schedule_state,
                                                new_update_event_time)

    def _get_ajusted_next_event_time(self, now, next_event_time):
        _log.debug("_get_adjusted_next_event_time")
        latest_next = now + datetime.timedelta(seconds=self.schedule_publish_interval)
        # Round to the next second to fix timer goofyness in agent timers.
        if latest_next.microsecond:
            latest_next = latest_next.replace(microsecond=0) + datetime.timedelta(seconds=1)
        if next_event_time is None or latest_next < next_event_time:
            return latest_next
        return next_event_time

    def _update_schedule_state(self, now):
        self._update_device_state_and_schedule(now)

    def _handle_remote_error(self, ex, point, headers):
        try:
            exc_type = ex.exc_info['exc_type']
            exc_args = ex.exc_info['exc_args']
        except KeyError:
            exc_type = "RemoteError"
            exc_args = ex.message
        error = {'type': exc_type, 'value': str(exc_args)}
        self._push_result_topic_pair(ERROR_RESPONSE_PREFIX,
                                    point, headers, error)

        _log.debug('Actuator Agent Error: ' + str(error))

    def _handle_standard_error(self, ex, point, headers):
        error = {'type': ex.__class__.__name__, 'value': str(ex)}
        self._push_result_topic_pair(ERROR_RESPONSE_PREFIX,
                                    point, headers, error)
        _log.debug('Actuator Agent Error: ' + str(error))

    def handle_get(self, peer, sender, bus, topic, headers, message):
        """
        Requests up to date value of a point.
        
        To request a value publish a message to the following topic:

        ``devices/actuators/get/<device path>/<actuation point>``
        
        with the fallowing header:
        
        .. code-block:: python
        
            {
                'requesterID': <Agent ID>
            }
        
        The ActuatorAgent will reply on the **value** topic 
        for the actuator:

        ``devices/actuators/value/<full device path>/<actuation point>``
        
        with the message set to the value the point.
        
        """
        point = topic.replace(topics.ACTUATOR_GET() + '/', '', 1)
        requester = headers.get('requesterID')
        headers = self._get_headers(requester)
        try:
            value = self.get_point(point)
            self._push_result_topic_pair(VALUE_RESPONSE_PREFIX,
                                        point, headers, value)
        except RemoteError as ex:
            self._handle_remote_error(ex, point, headers)
        except StandardError as ex:
            self._handle_standard_error(ex, point, headers)

    def handle_set(self, peer, sender, bus, topic, headers, message):
        """
        Set the value of a point.
        
        To set a value publish a message to the following topic:

        ``devices/actuators/set/<device path>/<actuation point>``
        
        with the fallowing header:
        
        .. code-block:: python
        
            {
                'requesterID': <Agent ID>
            }
        
        The ActuatorAgent will reply on the **value** topic 
        for the actuator:

        ``devices/actuators/value/<full device path>/<actuation point>``
        
        with the message set to the value the point.
        
        Errors will be published on 
        
        ``devices/actuators/error/<full device path>/<actuation point>``
        
        with the same header as the request.
        
        """
        if sender == 'pubsub.compat':
            message = compat.unpack_legacy_message(headers, message)

        point = topic.replace(topics.ACTUATOR_SET() + '/', '', 1)
        requester = headers.get('requesterID')
        headers = self._get_headers(requester)
        if not message:
            error = {'type': 'ValueError', 'value': 'missing argument'}
            _log.debug('ValueError: ' + str(error))
            self._push_result_topic_pair(ERROR_RESPONSE_PREFIX,
                                        point, headers, error)
            return

        try:
            self.set_point(requester, point, message)
        except RemoteError as ex:
            self._handle_remote_error(ex, point, headers)
        except StandardError as ex:
            self._handle_standard_error(ex, point, headers)

    @RPC.export
    def get_point(self, topic, **kwargs):
        """
        RPC method
        
        Gets up to date value of a specific point on a device. 
        Does not require the device be scheduled. 
        
        :param topic: The topic of the point to grab in the 
                      format <device topic>/<point name>
        :param \*\*kwargs: Any driver specific parameters
        :type topic: str
        :returns: point value
        :rtype: any base python type"""
        topic = topic.strip('/')
        _log.debug('handle_get: {topic}'.format(topic=topic))
        path, point_name = topic.rsplit('/', 1)
        return self.vip.rpc.call(self.driver_vip_identity, 'get_point', path, point_name, **kwargs).get()

    @RPC.export
    def set_point(self, requester_id, topic, value, **kwargs):
        """RPC method
        
        Sets the value of a specific point on a device. 
        Requires the device be scheduled by the calling agent.
        
        :param requester_id: Identifier given when requesting schedule. 
        :param topic: The topic of the point to set in the 
                      format <device topic>/<point name>
        :param value: Value to set point to.
        :param \*\*kwargs: Any driver specific parameters
        :type topic: str
        :type requester_id: str
        :type value: any basic python type
        :returns: value point was actually set to. Usually invalid values 
                cause an error but some drivers (MODBUS) will return a different
                value with what the value was actually set to.
        :rtype: any base python type
        
        .. warning:: Calling without previously scheduling a device and not within 
                     the time allotted will raise a LockError"""
                     
        topic = topic.strip('/')
        _log.debug('handle_set: {topic},{requester_id}, {value}'.
                   format(topic=topic, requester_id=requester_id, value=value))

        path, point_name = topic.rsplit('/', 1)

        headers = self._get_headers(requester_id)
        if not isinstance(requester_id, str):
            raise TypeError("Agent id must be a nonempty string")
        if self._check_lock(path, requester_id):
            result = self.vip.rpc.call(self.driver_vip_identity, 'set_point', path, point_name, value, **kwargs).get()

            headers = self._get_headers(requester_id)
            self._push_result_topic_pair(WRITE_ATTEMPT_PREFIX,
                                        topic, headers, value)
            self._push_result_topic_pair(VALUE_RESPONSE_PREFIX,
                                        topic, headers, result)
        else:
            raise LockError("caller ({}) does not have this lock".format(requester_id))

        return result
    
    def handle_revert_point(self, peer, sender, bus, topic, headers, message):
        """
        Revert the value of a point.
        
        To revert a value publish a message to the following topic:

        ``actuators/revert/point/<device path>/<actuation point>``
        
        with the fallowing header:
        
        .. code-block:: python
        
            {
                'requesterID': <Agent ID>
            }
        
        The ActuatorAgent will reply on

        ``devices/actuators/reverted/point/<full device path>/<actuation point>``
        
        This is to indicate that a point was reverted.
        
        Errors will be published on 
        
        ``devices/actuators/error/<full device path>/<actuation point>``
        
        with the same header as the request.
        """
        point = topic.replace(topics.ACTUATOR_REVERT_POINT()+'/', '', 1)
        requester = headers.get('requesterID')
        headers = self._get_headers(requester)
        
        try:
            self.revert_point(requester, point)
        except RemoteError as ex:
            self._handle_remote_error(ex, point, headers)
        except StandardError as ex:
            self._handle_standard_error(ex, point, headers)
            
    def handle_revert_device(self, peer, sender, bus, topic, headers, message):
        """
        Revert all the writable values on a device.
        
        To revert a device publish a message to the following topic:

        ``devices/actuators/revert/device/<device path>``
        
        with the fallowing header:
        
        .. code-block:: python
        
            {
                'requesterID': <Agent ID>
            }
        
        The ActuatorAgent will reply on the **value** topic 
        for the actuator:

        ``devices/actuators/reverted/device/<full device path>``
        
        to indicate that a point was reverted.
        
        Errors will be published on 
        
        ``devices/actuators/error/<full device path>/<actuation point>``
        
        with the same header as the request.
        """
        point = topic.replace(topics.ACTUATOR_REVERT_DEVICE()+'/', '', 1)
        requester = headers.get('requesterID')
        headers = self._get_headers(requester)
        
        try:
            self.revert_device(requester, point)
        except RemoteError as ex:
            self._handle_remote_error(ex, point, headers)
        except StandardError as ex:
            self._handle_standard_error(ex, point, headers)
    
    @RPC.export
    def revert_point(self, requester_id, topic, **kwargs):  
        """
        RPC method
        
        Reverts the value of a specific point on a device to a default state. 
        Requires the device be scheduled by the calling agent.
        
        :param requester_id: Identifier given when requesting schedule. 
        :param topic: The topic of the point to revert in the 
                      format <device topic>/<point name>
        :param \*\*kwargs: Any driver specific parameters
        :type topic: str
        :type requester_id: str
        
        .. warning:: Calling without previously scheduling a device and not within 
                     the time allotted will raise a LockError"""
                     
        topic = topic.strip('/')
        _log.debug('handle_revert: {topic},{requester_id}'.
                   format(topic=topic, requester_id=requester_id))
        
        path, point_name = topic.rsplit('/', 1)
        
        headers = self._get_headers(requester_id)
        
        if self._check_lock(path, requester_id):
            self.vip.rpc.call(self.driver_vip_identity, 'revert_point', path, point_name, **kwargs).get()
    
            headers = self._get_headers(requester_id)
            self._push_result_topic_pair(REVERT_POINT_RESPONSE_PREFIX,
                                        topic, headers, None)
        else:
            raise LockError("caller does not have this lock")
        
    @RPC.export
    def revert_device(self, requester_id, topic, **kwargs):  
        """
        RPC method
        
        Reverts all points on a device to a default state. 
        Requires the device be scheduled by the calling agent.
        
        :param requester_id: Identifier given when requesting schedule. 
        :param topic: The topic of the device to revert
        :param \*\*kwargs: Any driver specific parameters
        :type topic: str
        :type requester_id: str
        
        .. warning:: Calling without previously scheduling a device and not within 
                     the time allotted will raise a LockError"""
                     
        topic = topic.strip('/')
        _log.debug('handle_revert: {topic},{requester_id}'.
                   format(topic=topic, requester_id=requester_id))
        
        path = topic
        
        headers = self._get_headers(requester_id)
        
        if self._check_lock(path, requester_id):
            self.vip.rpc.call(self.driver_vip_identity, 'revert_device', path, **kwargs).get()
    
            headers = self._get_headers(requester_id)
            self._push_result_topic_pair(REVERT_DEVICE_RESPONSE_PREFIX,
                                        topic, headers, None)
        else:
            raise LockError("caller does not have this lock")

    def _check_lock(self, device, requester):
        _log.debug('_check_lock: {device}, {requester}'.format(device=device,
                                                              requester=requester))
        device = device.strip('/')
        if device in self._device_states:
            device_state = self._device_states[device]
            return device_state.agent_id == requester
        return False

    def handle_schedule_request(self, peer, sender, bus, topic, headers, message):
        """        
        Schedule request pub/sub handler
        
        An agent can request a task schedule by publishing to the
        ``devices/actuators/schedule/request`` topic with the following header:
        
        .. code-block:: python
        
            {
                'type': 'NEW_SCHEDULE',
                'requesterID': <Agent ID>, #The name of the requesting agent.
                'taskID': <unique task ID>, #The desired task ID for this task. It must be unique among all other scheduled tasks.
                'priority': <task priority>, #The desired task priority, must be 'HIGH', 'LOW', or 'LOW_PREEMPT'
            }
            
        The message must describe the blocks of time using the format described in `Device Schedule`_. 
            
        A task may be canceled by publishing to the
        ``devices/actuators/schedule/request`` topic with the following header:
        
        .. code-block:: python
        
            {
                'type': 'CANCEL_SCHEDULE',
                'requesterID': <Agent ID>, #The name of the requesting agent.
                'taskID': <unique task ID>, #The task ID for the canceled Task.
            }
            
        requesterID
            The name of the requesting agent.
        taskID
            The desired task ID for this task. It must be unique among all other scheduled tasks.
        priority
            The desired task priority, must be 'HIGH', 'LOW', or 'LOW_PREEMPT'
            
        No message is requires to cancel a schedule.
            
        """
        if sender == 'pubsub.compat':
            message = compat.unpack_legacy_message(headers, message)

        request_type = headers.get('type')
        _log.debug('handle_schedule_request: {topic}, {headers}, {message}'.
                   format(topic=topic, headers=str(headers), message=str(message)))

        requester_id = headers.get('requesterID')
        task_id = headers.get('taskID')
        priority = headers.get('priority')

        if request_type == SCHEDULE_ACTION_NEW:
            try:
                if len(message) == 1:
                    requests = message[0]
                else:
                    requests = message

                self.request_new_schedule(requester_id, task_id, priority, requests)
            except StandardError as ex:
                return self._handle_unknown_schedule_error(ex, headers, message)

        elif request_type == SCHEDULE_ACTION_CANCEL:
            try:
                self.request_cancel_schedule(requester_id, task_id)
            except StandardError as ex:
                return self._handle_unknown_schedule_error(ex, headers, message)
        else:
            _log.debug('handle-schedule_request, invalid request type')
            self.vip.pubsub.publish('pubsub', topics.ACTUATOR_SCHEDULE_RESULT(), headers,
                                    {'result': SCHEDULE_RESPONSE_FAILURE,
                                     'data': {},
                                     'info': 'INVALID_REQUEST_TYPE'})

    @RPC.export
    def request_new_schedule(self, requester_id, task_id, priority, requests):
        """
        RPC method
        
        Requests one or more blocks on time on one or more device.
        
        :param requester_id: Requester name. 
        :param task_id: Task name.
        :param priority: Priority of the task. Must be either "HIGH", "LOW", or "LOW_PREEMPT"
        :param requests: A list of time slot requests in the format described in `Device Schedule`_.
        
        :type requester_id: str
        :type task_id: str
        :type priority: str
        :type request: list
        :returns: Request result
        :rtype: dict       
        
        :Return Values:
        
            The return values are described in `New Task Response`_.
        """
                     
        now = datetime.datetime.now()

        topic = topics.ACTUATOR_SCHEDULE_RESULT()
        headers = self._get_headers(requester_id, task_id=task_id)
        headers['type'] = SCHEDULE_ACTION_NEW

        try:
            if requests and isinstance(requests[0], basestring):
                requests = [requests]
            requests = [[r[0].strip('/'),utils.parse_timestamp_string(r[1]),utils.parse_timestamp_string(r[2])] for r in requests]

        except StandardError as ex:
            return self._handle_unknown_schedule_error(ex, headers, requests)

        _log.debug("Got new schedule request: {}, {}, {}, {}".
                   format(requester_id, task_id, priority, requests))

        result = self._schedule_manager.request_slots(requester_id, task_id, requests, priority, now)
        success = SCHEDULE_RESPONSE_SUCCESS if result.success else SCHEDULE_RESPONSE_FAILURE

        # Dealing with success and other first world problems.
        if result.success:
            self._update_device_state_and_schedule(now)
            for preempted_task in result.data:
                preempt_headers = self._get_headers(preempted_task[0], task_id=preempted_task[1])
                preempt_headers['type'] = SCHEDULE_ACTION_CANCEL
                self.vip.pubsub.publish('pubsub', topic, headers=preempt_headers,
                                        message={'result': SCHEDULE_CANCEL_PREEMPTED,
                                                 'info': '',
                                                 'data': {'agentID': requester_id,
                                                          'taskID': task_id}})

        # If we are successful we do something else with the real result data
        data = result.data if not result.success else {}

        results = {'result': success,
                   'data': data,
                   'info': result.info_string}
        self.vip.pubsub.publish('pubsub', topic, headers=headers, message=results)

        return results

    def _handle_unknown_schedule_error(self, ex, headers, message):
        _log.error(
            'bad request: {header}, {request}, {error}'.format(header=headers, request=message, error=str(ex)))
        results = {'result': "FAILURE",
                   'data': {},
                   'info': 'MALFORMED_REQUEST: ' + ex.__class__.__name__ + ': ' + str(ex)}
        self.vip.pubsub.publish('pubsub', topics.ACTUATOR_SCHEDULE_RESULT(), headers=headers, message=results)
        return results

    @RPC.export
    def request_cancel_schedule(self, requester_id, task_id):
        """RPC method
        
        Requests the cancelation of the specified task id.
        
        :param requester_id: Requester name. 
        :param task_id: Task name.
        
        :type requester_id: str
        :type task_id: str
        :returns: Request result
        :rtype: dict
        
        :Return Values: 

        The return values are described in `Cancel Task Response`_.
        
        """
        now = datetime.datetime.now()
        headers = self._get_headers(requester_id, task_id=task_id)
        headers['type'] = SCHEDULE_ACTION_CANCEL

        result = self._schedule_manager.cancel_task(requester_id, task_id, now)
        success = SCHEDULE_RESPONSE_SUCCESS if result.success else SCHEDULE_RESPONSE_FAILURE

        topic = topics.ACTUATOR_SCHEDULE_RESULT()
        message = {'result': success,
                   'info': result.info_string,
                   'data': {}}
        self.vip.pubsub.publish('pubsub', topic,
                                headers=headers,
                                message=message)

        if result.success:
            self._update_device_state_and_schedule(now)

        return message

    def _get_headers(self, requester, time=None, task_id=None):
        headers = {}
        if time is not None:
            headers['time'] = time
        else:
            utcnow = datetime.datetime.utcnow()
            headers = {'time': utils.format_timestamp(utcnow)}
        if requester is not None:
            headers['requesterID'] = requester
        if task_id is not None:
            headers['taskID'] = task_id
        return headers

    def _push_result_topic_pair(self, prefix, point, headers, value):
        topic = normtopic('/'.join([prefix, point]))
        self.vip.pubsub.publish('pubsub', topic, headers, message=value)

    


def main():
    '''Main method called to start the agent.'''
    utils.vip_main(actuator_agent)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
