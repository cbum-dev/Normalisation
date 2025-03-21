# Basic normalisation steps





```
{ k: d, ...rest } if k in SCHEMA_OBJECT_KEYS
->
{ k: {(a, if b not is list then canonicalish(b) else b) | (a, b) in d}, ...rest }
```

If there is a schema object key present, then map each value in its dictionary to its canonicalised value if it is not a list else keep it as is.

<br>

## `multipleOf`

#### 1.

```
{ multipleOf: m, ...rest }
->
{ multipleOf: abs(m), ...rest }
```

Make the multipleOf value equal to its absolute value, since a multiple of -n is also a multiple of n.

<br>

## `properties`

#### 1.

```
{ properties: p, additionalProperties: FALSEY, maxProperties?: m, ...rest } if patternProperties absent
->
{ properties: {(k, v) | (k, v) if v is not FALSEY}, additionalProperties: FALSEY, maxProperties: min(m | inf, len(properties)) }
```

If there are properties present and additionalProperties is FALSEY, keep only the mappings in properties where the value is not FALSEY and update maxProperties.

#### 2.

```
{ maxProperties: 0, properties?: _, patternProperties?: _, additionalProperties?: _, ...rest }
->
{ maxProperties: 0, ...rest }
```

If maxProperties is zero, remove properties, patternProperties, and additionalProperties if present.

<br>

## `dependencies`

#### 1.

```
{ dependencies: d, ...rest }
->
{ dependencies: {(k, v) | (k, v) in d if v not [] or TRUTHY}, ...rest }
```

If there are dependencies present, keep each mapping if the value is not an empty list or truthy.

<br>

## `keywords`

#### 1.

```
{ minItems: 0, ...rest}
->
{ ...rest }
```

If the minItems is zero, simply remove the field because minItems defaults to zero.

#### 2.

```
{ items: {}, ...rest}
->
{ ...rest }
```

If there are no items, simply remove the field.

#### 3.

```
{ additionalItems: {}, ...rest}
->
{ ...rest }
```

If there are no additionalItems, simply remove the field.

#### 4.

```
{ dependencies: {}, ...rest}
->
{ ...rest }
```

If there are no dependencies, simply remove the field.

#### 5.

```
{ minProperties: 0, ...rest}
->
{ ...rest }
```

If the minProperties is zero, simply remove the field because minProperties defaults to zero.

#### 6.

```
{ properties: {}, ...rest}
->
{ ...rest }
```

If there are no properties, simply remove the field.

#### 7.

```
{ propertyNames: {}, ...rest}
->
{ ...rest }
```

If there are no propertyNames, simply remove the field.

#### 8.

```
{ patternProperties: {}, ...rest}
->
{ ...rest }
```

If there are no patternProperties, simply remove the field.

#### 9.

```
{ additionalProperties: {}, ...rest}
->
{ ...rest }
```

If there are no additionalProperties, simply remove the field.

#### 10.

```
{ required: [], ...rest}
->
{ ...rest }
```

If there are no required properties, simply remove the field.

<br>

## `anyOf`

#### 1.

```
{ anyOf: xs, ...rest } if TRUTHY in xs
->
{ ...rest }
```

If TRUTHY is one of the options in anyOf, simply remove the field since it would match any input.

<br>

## `allOf`

#### 1.

```
{ allOf: xs, ...rest } if FALSEY in xs
->
FALSEY
```

If FALSEY is present in allOf, return FALSEY since it would not be possible to match any input.

#### 2.

```
{ allOf: xs, ...rest } if (x is TRUTHY | x in xs)
->
{ ...rest }
```

If all the values in allOf are TRUTHY, simply remove the field since it would match any input.

#### 3.

```
{ allOf: [x], ...rest }
->
x
```

If there is only one condition in allOf, simply return that condition.

<br>

## `oneOf`

#### 1.

```
{ oneOf: xs, ...rest } if (x is FALSEY | x in xs)
->
FALSEY
```

If all the options in oneOf are FALSEY, simply return FALSEY since it would not be possible to match any input.

#### 2.

```
{ oneOf: xs, ...rest } if count(xs, TRUTHY) > 1
->
FALSEY
```

#### 3.

```
{ oneOf: xs, ...rest }
->
{ oneOf: [x | x in xs if x is not FALSEY], ...rest }
```

If an option in oneOf is FALSEY, it can be removed, since that option could never be selected.

<br>

## `uniqueItems`

#### 1.

```
{ uniqueItems: false, ...rest }
->
{ ...rest }
```

If uniqueItems is false, the field can be removed, since uniqueItems defaults to false.

<br>

# Types

The above normalisation rules were simple, they provided a clear idea of what the schema would normalise to.
However, the canonicalish function also makes use of possible types the schema could adhere to.
The function will compute the possible types associated with a schema by calling [`get_type`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L308).
It will then use different rules to check whether it would be possible for the schema to be of this type.
For example, if a schema includes the type "number", but the lower bound is higher than the upper bound, no number could represent it. For that reason, the "number" type can be removed.

To describe these steps, the schema (`s`) and the array of possible types (`t`) will be represented as `(s, t)`.
This allows normalisation rules to be defined in which `(s, t)` steps to `(s', t')`, i.e.:

```
(s, t)
->
(s', t')
```

<br>

In the earlier example, this would be:

```
({ ...rest }, t) if "number" in t and lower_bound > upper_bound
->
({ ...rest }, t - "number")
```

This means that if "number" is in the type list of a schema in which the lower bound exceeds the upper bound, "number" is removed from the list of types since it would not be possible to be represented.
Another example could be a schema and type list including "array", but where the minItems exceed the maxItems, meaning it cannot actually be represented by an "array".

Once the function has computed which types are associated with the schema, it removes keywords specific to types not being representable in the given schema. For example, if "number" is not a possible type, fields such as multipleOf, maximum, and minimum will be removed.
The next step is returning a schema based on the possible types or injecting the possible types in the "type" field of the schema. For example, if the function concludes that there are no types to describe the schema, it returns FALSEY. These rules can be found under [types to schema](#types-to-schema).

<br>

## `"number"`

#### 1.

```
({ exclusiveMinimum: False, ...rest }, t) if "number" in t
->
({ ...rest}, t)
```

#### 2.

```
({ exclusiveMaximum: False, ...rest }, t) if "number" in t
->
({ ...rest}, t)
```

#### 3.

```
({ multipleOf: n, ...rest }, t) if "number" in t and n is int
->
({ multipleOf: n, ...rest }, t + "integer" - "number")
```

#### 4.

```
({ multipleOf: n, ...rest }, t) if "number" in t and no multipleOf possible within lower_bound to higher_bound
->
({ multipleOf: n, ...rest }, t - "number")
```

#### 5.

```
({ ...rest }, t) if "number" in t and lower_bound > higher_bound
->
({ ...rest }, t - "number")
```

#### 6.

```
({ ...rest }, ["number"]) if lower_bound == higher_bound
->
({ const: lower_bound }, ["number"])
```

<br>

## `"integer"`

#### 1.

```
({ multipleOf: m, ...rest }, t) if "integer" in t and "number" not in t and m is of form 1/n
->
({ ...rest }, t)
```

#### 2.

```
({ minimum: m, exlusiveMinimum: True, ...rest }, t) if "integer" in t
->
({ minimum: if ceil(m) == m then m + 1 else m, ...rest }, t)
```

#### 3.

```
({ minimum: m, exlusiveMaximum: True, ...rest }, t) if "integer" in t
->
({ minimum: if floor(m) == m then m - 1 else m, ...rest }, t)
```

#### 4.

```
({ ...rest }, t) if "integer" in t and lower_bound > higher_bound
->
({ ...rest }, t - "integer")
```

#### 5.

```
({ ...rest }, ["integer"]) if lower_bound == higher_bound
->
({ const: lower_bound }, ["integer"])
```

<br>

## `"array"`

#### 1.

```
({ contains: FALSEY, ...rest }, t) if "array" in t
->
({ contains: FALSEY, ...rest }, t - "array")
```

#### 2.

```
({ contains: TRUTHY, minItems?: m, ...rest }, t) if "array" in t
->
({ minItems: max(m | 1, 1), ...rest }, t)
```

#### 3.

```
({ uniqueItems: u, items: i, ...rest }, t) if "array" in t and i is dict and upper_bound of instances in i is finite
->
({ uniqueItems: u, items: i, maxItems: upper_bound, ...rest }, t)
```

#### 4.

```
({ ...rest }, t) if "array" in t and minItems > maxItems
->
({ ...rest }, t - "array")
```

#### 5.

```
({ minItems: m, items: i, ...rest }, t) if "array" in t and i is dict and upper_bound of instances in i == 0 and m > 0
->
({ minItems: m, items: i, ...rest }, t - "array")
```

#### 6.

```
({ minItems: m, items: i, uniqueItems: True, ...rest }, t) if "array" in t and i is dict and upper_bound of instances in i < m
->
({ minItems: m, items: i, uniqueItems: True, ...rest }, t - "array")
```

#### 7.

```
({ items: i, additionalItems: FALSEY, maxItems: _, ...rest }, t) if "array" in t and i is list
->
({ items: i, additionalItems: FALSEY, ...rest }, t)
```

#### 8.

```
({ items: FALSEY, uniqueItems: ?: _, additionalItems?: _, ...rest }, t) if "array" in t
->
({ maxItems: 0, ...rest }, t)
```

#### 9.

```
({ maxItems: 0, items?: _, uniqueItems?: _, additionalItems?: _, ...rest }, t) if "array" in t
->
({ maxItems: 0, ...rest }, t)
```

#### 10.

```
({ items: TRUTHY, ...rest }, t) if "array" in t
->
({ ...rest }, t)
```

<br>

## Types to schema

#### 1.

```
({ ...rest }, [])
->
FALSEY
```

#### 2.

```
({ ...rest }, ["null"])
->
{ const: None }
```

#### 3.

```
({ ...rest }, ["boolean"])
->
{ enum: [False, True] }
```

#### 4.

```
({ ...rest }, ["null", "boolean"])
->
{ enum: [None, False, True] }
```

#### 5.

```
({ ...rest }, [t0])
->
{ type: t0, ...rest }
```

#### 6.

```
({ type: _, ...rest }, t) if t == get_type({})
->
{ ...rest }
```

#### 7.

<!-- Note: only applies if none of the above apply -->

```
({ ...rest }, t)
->
{ type: t, ...rest }
```

<br>

# Terminology

a. [`canonicalish`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L239)

b. [`TRUTHY`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L615) = `canonicalish(True)`

c. [`FALSEY`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L616) = `canonicalish(False)`

d. [`SCHEMA_KEYS`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L52-L55)

e. [`SCHEMA_OBJECT_KEYS`](https://github.com/python-jsonschema/hypothesis-jsonschema/blob/72c50adbce269b404267fc3cdfaa0499e041bb02/src/hypothesis_jsonschema/_canonicalise.py#L58)
