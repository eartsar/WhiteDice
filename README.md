###Discord Dicebot for Whitehack

Other dicebots are not well suited to Whitehack which uses an 
unusual roll-high-under mechanic.  Most attack rolls and tests can involve
rolling high enough to beat or equal a target number, but under or equal to an ability
score or statistic.  Many Whitehack rolls can be expressed as:

`1d20 >= target <= stat`

Attacks are resolved by rolling a `1d20` and beating the opponent's armor class,
while still rolling under your attack value.

Additionally the system makes use of _double positive_ and _double negative_ rolls, where
the better or worse roll on a `1d20` is taken, respectively.  Roles to hit opponents or
succeed at tests can be made with a _double positive_ or _double negative_ - and these
may also incorporate bonueses such as _combat advantage_.  Because of the unusual 
roll-high-under mechanic - a bonus is expressed by _adding_ to the ability score or
statistic being rolled against.  Examples:

* A Dexterity Test with double positive.  Roll `1d20` twice and the higher roll that is still under 
dexterity is taken.  If both are over, it's still a failure.  If both are over and one is a fumble `(20)`
the simple failure is taken.  If both are equal or under - the highest roll that is equal to or under
the stat is taken.  If both are critical successes - both roll exactly the stat that is _awesome_.
* An attack with combat advantage.  Simply add `+2` to the attack value and roll `1d20` and compare the
roll against the slightly higher attack value;  if the roll is over the opponent's armor class and equal
to or under the (slightly improved) attack value it is successful.

TBD More to come.
