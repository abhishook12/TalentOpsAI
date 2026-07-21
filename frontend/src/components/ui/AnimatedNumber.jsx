import React, { useEffect } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export default function AnimatedNumber({ value, formatter = (v) => v.toLocaleString() }) {
  const springValue = useSpring(value, {
    stiffness: 100,
    damping: 30,
    mass: 1,
  });

  useEffect(() => {
    springValue.set(value);
  }, [value, springValue]);

  const display = useTransform(springValue, (current) => formatter(Math.round(current)));

  return <motion.span>{display}</motion.span>;
}
