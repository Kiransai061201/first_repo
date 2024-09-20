import React, { useState, useEffect, useRef } from 'react';
const Block = ({ id, content, connections, onConnect }) => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const blockRef = useRef(null);
  const handleMouseDown = (event) => {
    setIsDragging(true);
    const offset = { x: event.clientX - position.x, y: event.clientY - position.y };
    const moveBlock = (moveEvent) => {
      setPosition({
        x: moveEvent.clientX - offset.x,
        y: moveEvent.clientY - offset.y,
      });
    };
    const stopDragging = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove




