# The Lantern Lab Field Handbook

The Lantern Lab is a fictional student engineering team that studies indoor air quality in the
imaginary Northbridge Learning Center. This handbook is original demonstration material created
for GroundNote. Its people, places, measurements, and procedures are fictional.

## Project Goal

The team builds small battery-powered sensor stations called Lantern Nodes. A node measures carbon
dioxide, temperature, and relative humidity in study rooms. The project goal is not to certify a
building or make medical claims. It helps students compare rooms, notice ventilation patterns, and
practice working with time-series data.

The pilot covers three rooms: Cedar, Maple, and Willow. Cedar is a quiet room with twelve seats.
Maple is a group room with twenty-four seats. Willow is a computer room with eighteen workstations.
The team chose these rooms because their occupancy patterns differ.

## Lantern Node Hardware

Each Lantern Node contains a carbon-dioxide sensor, a combined temperature and humidity sensor, a
microcontroller, local flash storage, and a rechargeable battery. The enclosure has side vents so
room air can reach the sensors. It must remain at least one metre from an open window, direct
sunlight, a heater, or a person's usual seat.

Nodes record one sample every 30 seconds. They store data locally as comma-separated values. The
columns are timestamp, node ID, room, carbon dioxide in parts per million, temperature in degrees
Celsius, relative humidity as a percentage, and battery voltage. Nodes do not record sound, video,
names, device addresses, or account identifiers.

## Deployment Plan

The pilot runs for ten school days. On the morning of day one, the team places Node L-01 in Cedar,
Node L-02 in Maple, and Node L-03 in Willow. A paper sign explains that the devices measure room
conditions and do not identify people.

The operations lead checks each node at 09:00 and 16:00. The morning check confirms that the vents
are clear, the battery is above 3.7 volts, and the node clock is within one minute of the reference
clock. The afternoon check copies the CSV file to the encrypted project laptop and records a short
equipment note. Raw files remain on that laptop; they are not uploaded to a shared cloud drive.

If a node is moved, covered, or exposed to water, the team marks the affected time range as invalid.
The node is then dried or repositioned before measurements continue. The team never edits raw CSV
values. Corrections and exclusions live in a separate audit note.

## Data Quality Rules

A sample is considered structurally valid when all required columns are present, the timestamp is
parseable, and the node ID matches the deployment plan. The expected operating ranges are 350 to
5,000 ppm for carbon dioxide, 10 to 35 °C for temperature, 10% to 90% for relative humidity, and
3.3 to 4.2 volts for the battery.

Values outside an expected range are flagged for review rather than silently deleted. A gap longer
than two minutes is also flagged. The analyst compares every flag with equipment notes. For example,
a low battery flag near 3.3 volts may explain a later data gap, while an abrupt temperature rise may
match a note that the node was moved into sunlight.

The team calculates five-minute medians for room comparisons. Medians reduce the influence of a
single noisy sample while preserving longer changes. Raw 30-second samples remain available for
auditing.

## Ventilation Observation Exercise

The exercise uses carbon dioxide as a classroom discussion signal, not as a direct health verdict.
For this fictional pilot, the team labels a five-minute median below 800 ppm as Low, 800–1,200 ppm
as Watch, and above 1,200 ppm as Review. These labels are internal teaching categories, not legal or
medical thresholds.

When a room reaches Review, students first confirm that the sensor is correctly placed and the
reading persists for at least two consecutive five-minute windows. They then compare occupancy notes
and window status. If a window was opened and the median falls, the report describes an association;
it does not claim that the window was the only cause.

## Pilot Findings

The fictional summary contains three observations. Cedar stayed in the Low category during most
quiet study periods. Maple entered Review on four afternoons when group sessions filled most seats;
its median usually returned to Watch within fifteen minutes after the scheduled ventilation break.
Willow remained in Watch for much of the day and showed the highest median temperature, 25.8 °C,
during workstation workshops.

Maple had the largest carbon-dioxide variation. Willow had the highest temperature but not the
highest carbon-dioxide peak. Cedar had the fewest missing samples. Node L-03 in Willow produced a
six-minute gap on day seven; the equipment note records a battery voltage of 3.31 volts before the
gap and a recharge afterward.

These observations do not prove causation. Occupancy notes were approximate, door position was not
recorded continuously, and the ten-day period was too short to represent every season.

## Roles and Review

The project has four rotating roles. The operations lead deploys and checks nodes. The data steward
copies files, verifies checksums, and controls the encrypted project laptop. The analyst applies the
published validation rules and produces charts. The reviewer checks calculations, labels, and
claims before the weekly summary is shared.

No student reviews their own weekly summary alone. The analyst and reviewer must be different
people. A release checklist confirms that charts have units, flagged gaps are disclosed, raw files
were not modified, and conclusions distinguish observation from causation.

## Privacy and Retention

Lantern Nodes intentionally collect no names, audio, images, network identifiers, or precise seat
locations. Approximate room occupancy is written as a count, not a list of people. The encrypted
project laptop is the only location for raw pilot files.

Raw CSV files are retained for 30 days after the class presentation. Validated five-minute medians
and anonymous equipment notes are retained for one semester so another class can reproduce the
analysis. At the end of each retention period, the data steward deletes the relevant files and the
reviewer records completion in the project log.

## Incident Procedure

If a laptop is lost, a raw file appears in an unapproved location, or a node unexpectedly contains
identifying data, collection stops. The operations lead disconnects the affected equipment, the data
steward preserves only the minimum evidence needed to understand the incident, and the instructor is
notified. Work resumes only after the team documents the cause and corrective action.

A normal sensor fault is handled differently. The team flags the time range, checks the battery and
placement, replaces the node if needed, and keeps the original raw file unchanged. Sensor faults are
reported in the limitations section of the weekly summary.

## Study Questions the Handbook Can Support

The handbook supports factual questions about sampling, room assignments, roles, retention, and
limits. It also supports comparisons between Cedar, Maple, and Willow; summaries of the deployment
or incident procedure; and questions about why the team uses medians or separates raw data from
audit notes. It contains no information about weather satellites, marine biology, financial markets,
or real people, so questions about those topics should receive an evidence-not-found response.
