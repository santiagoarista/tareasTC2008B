/*
 * Script to draw a color polygon using WebGL 2
 * Also using external functions to abstract commonly used code
 *
 * Santiago Arista Viramontes
 * 2025-11-11
 */


'use strict';

import * as twgl from "twgl-base.js";
import { M3 } from "../libs/2d-lib";
import GUI from 'lil-gui';

// Vertex Shader as a string
const vsGLSL = `#version 300 es
in vec4 a_position;
in vec4 a_color;

uniform vec2 u_resolution;
uniform mat3 u_transforms;

out vec4 v_color;

void main() {
    vec2 position = (u_transforms * vec3(a_position.xy, 1)).xy;
    vec2 clipSpace = (position / u_resolution) * 2.0 - 1.0;
    gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
    v_color = a_color;
}
`;

// Fragment Shader as a string
const fsGLSL = `#version 300 es
precision highp float;

in vec4 v_color;

out vec4 outColor;

void main() {
    outColor = v_color;
}
`;


// Structure for the global data of all objects
// This data will be modified by the UI and used by the renderer
const objects = {
    smiley: {
        transforms: {
            t: {
                x: 250,
                y: 250,
                z: 0,
            },
            rr: {
                x: 0,
                y: 0,
                z: 0,
            },
            s: {
                x: 1,
                y: 1,
                z: 1,
            }
        },
        color: [1, 0.3, 0, 1],
    },
    pivot: {
        transforms: {
            t: {
                x: 250,
                y: 250,
                z: 0,
            },
            rr: {
                x: 0,
                y: 0,
                z: 0,
            },
            s: {
                x: 1,
                y: 1,
                z: 1,
            }
        },
        color: [1, 0.3, 0, 1],
    }
}

function drawScene(gl, vao, programInfo, bufferInfo, object, usePivot = false) {
    
    let translate = [object.transforms.t.x, object.transforms.t.y];
    let angle_radians = object.transforms.rr.z;
    let scale = [object.transforms.s.x, object.transforms.s.y];

    // Create transform matrices
    let transforms = M3.identity();
    
    if (usePivot) {
        // For smiley: rotate around pivot point
        // 1. Scale
        transforms = M3.multiply(M3.scale(scale), transforms);
        
        // 2. Translate to smiley position
        transforms = M3.multiply(M3.translation(translate), transforms);
        
        // 3. Translate by -pivot (move pivot to origin)
        let pivot = [objects.pivot.transforms.t.x, objects.pivot.transforms.t.y];
        transforms = M3.multiply(M3.translation([-pivot[0], -pivot[1]]), transforms);
        
        // 4. Rotate around origin (which is now the pivot point)
        transforms = M3.multiply(M3.rotation(angle_radians), transforms);
        
        // 5. Translate back by +pivot
        transforms = M3.multiply(M3.translation(pivot), transforms);
    } else {
        // For pivot: simple transformations
        const scaMat = M3.scale(scale);
        const rotMat = M3.rotation(angle_radians);
        const traMat = M3.translation(translate);
        
        transforms = M3.multiply(scaMat, transforms);
        transforms = M3.multiply(rotMat, transforms);
        transforms = M3.multiply(traMat, transforms);
    }

    let uniforms =
    {
        u_resolution: [gl.canvas.width, gl.canvas.height],
        u_transforms: transforms,
    }

    gl.useProgram(programInfo.program);

    twgl.setUniforms(programInfo, uniforms);

    gl.bindVertexArray(vao);

    twgl.drawBufferInfo(gl, bufferInfo);
}

function render(gl, smileyVao, smileyProgramInfo, smileyBufferInfo, pivotVao, pivotProgramInfo, pivotBufferInfo) {
    // Clear the canvas
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    // Draw smiley (with pivot rotation)
    drawScene(gl, smileyVao, smileyProgramInfo, smileyBufferInfo, objects.smiley, true);

    // Draw pivot (without pivot rotation)
    drawScene(gl, pivotVao, pivotProgramInfo, pivotBufferInfo, objects.pivot, false);

    requestAnimationFrame(() => render(gl, smileyVao, smileyProgramInfo, smileyBufferInfo, pivotVao, pivotProgramInfo, pivotBufferInfo));
}

function main() {
    const canvas = document.querySelector('canvas');
    const gl = canvas.getContext('webgl2');
    
    if (!gl) {
        console.error('WebGL2 not supported');
        return;
    }

    // Set canvas size
    canvas.width = 500;
    canvas.height = 500;
    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);

    setupUI(gl)

    const programInfo = twgl.createProgramInfo(gl, [vsGLSL, fsGLSL]);

    // Generate smiley face data
    const smileyArrays = generateSmileyData();
    const smileyBufferInfo = twgl.createBufferInfoFromArrays(gl, smileyArrays);
    const smileyVao = twgl.createVAOFromBufferInfo(gl, programInfo, smileyBufferInfo);

    // Generate pivot data
    const pivotArrays = generatePivotData();
    const pivotBufferInfo = twgl.createBufferInfoFromArrays(gl, pivotArrays);
    const pivotVao = twgl.createVAOFromBufferInfo(gl, programInfo, pivotBufferInfo);

    render(gl, smileyVao, programInfo, smileyBufferInfo, pivotVao, programInfo, pivotBufferInfo);

}

function setupUI(gl)
{
    const gui = new GUI();

    const traFolder = gui.addFolder('Translation');
    traFolder.add(objects.smiley.transforms.t, 'x', 0, gl.canvas.width);
    traFolder.add(objects.smiley.transforms.t, 'y', 0, gl.canvas.height);
    traFolder.add(objects.pivot.transforms.t, 'x', 0, gl.canvas.width);
    traFolder.add(objects.pivot.transforms.t, 'y', 0, gl.canvas.height);

    const rotFolder = gui.addFolder('Rotation');
    rotFolder.add(objects.smiley.transforms.rr, 'z', 0, Math.PI * 2);

    const scaFolder = gui.addFolder('Scale');
    scaFolder.add(objects.smiley.transforms.s, 'x', -5, 5);
    scaFolder.add(objects.smiley.transforms.s, 'y', -5, 5);

    gui.addColor(objects.smiley, 'color');
}

// Create the data for a smiley face
function generateSmileyData() {
    let arrays = {
        a_position: { numComponents: 2, data: [] },
        a_color:    { numComponents: 4, data: [] },
        indices:    { numComponents: 3, data: [] }
    };

    let vertexIndex = 0;

    // Helper function to add a circle
    function addCircle(centerX, centerY, radius, segments, r, g, b, a) {
        let centerIndex = vertexIndex++;
        
        // Add center vertex
        arrays.a_position.data.push(centerX, centerY);
        arrays.a_color.data.push(r, g, b, a);

        // Add perimeter vertices and create triangles
        for (let i = 0; i <= segments; i++) {
            let angle = (i / segments) * 2 * Math.PI;
            let x = centerX + radius * Math.cos(angle);
            let y = centerY + radius * Math.sin(angle);
            
            arrays.a_position.data.push(x, y);
            arrays.a_color.data.push(r, g, b, a);
            
            if (i > 0) {
                arrays.indices.data.push(centerIndex, vertexIndex - 1, vertexIndex);
            }
            vertexIndex++;
        }
    }

    // Helper function to add an arc (for the smile)
    function addArc(centerX, centerY, radius, startAngle, endAngle, segments, thickness, r, g, b, a) {
        // Create arc as a thick line using triangles
        for (let i = 0; i < segments; i++) {
            let angle1 = startAngle + (i / segments) * (endAngle - startAngle);
            let angle2 = startAngle + ((i + 1) / segments) * (endAngle - startAngle);
            
            // Inner arc points
            let x1Inner = centerX + (radius - thickness) * Math.cos(angle1);
            let y1Inner = centerY + (radius - thickness) * Math.sin(angle1);
            let x2Inner = centerX + (radius - thickness) * Math.cos(angle2);
            let y2Inner = centerY + (radius - thickness) * Math.sin(angle2);
            
            // Outer arc points
            let x1Outer = centerX + (radius + thickness) * Math.cos(angle1);
            let y1Outer = centerY + (radius + thickness) * Math.sin(angle1);
            let x2Outer = centerX + (radius + thickness) * Math.cos(angle2);
            let y2Outer = centerY + (radius + thickness) * Math.sin(angle2);
            
            // Add 4 vertices for this segment
            let baseIndex = vertexIndex;
            
            arrays.a_position.data.push(x1Inner, y1Inner);
            arrays.a_color.data.push(r, g, b, a);
            
            arrays.a_position.data.push(x1Outer, y1Outer);
            arrays.a_color.data.push(r, g, b, a);
            
            arrays.a_position.data.push(x2Inner, y2Inner);
            arrays.a_color.data.push(r, g, b, a);
            
            arrays.a_position.data.push(x2Outer, y2Outer);
            arrays.a_color.data.push(r, g, b, a);
            
            // Create two triangles for this segment
            arrays.indices.data.push(baseIndex, baseIndex + 1, baseIndex + 2);
            arrays.indices.data.push(baseIndex + 1, baseIndex + 3, baseIndex + 2);
            
            vertexIndex += 4;
        }
    }

    // Draw the face (yellow circle)
    addCircle(0, 0, 125.0, 64, 1.0, 1.0, 0.0, 1.0);

    // Draw left eye (black circle)
    addCircle(-45.0, -40.0, 15.0, 32, 0.0, 0.0, 0.0, 1.0);

    // Draw right eye (black circle)
    addCircle(45.0, -40.0, 15.0, 32, 0.0, 0.0, 0.0, 1.0);

    // Draw smile (black arc)
    // Arc from about 200 degrees to 340 degrees (bottom half)
    addArc(0, 20, -70, Math.PI * 1.2, Math.PI * 1.8, 32, 5, 0.0, 0.0, 0.0, 1.0);

    console.log(arrays);
    return arrays;
}

// Create the data for a pivot point (red circle)
function generatePivotData() {
    let arrays = {
        a_position: { numComponents: 2, data: [] },
        a_color:    { numComponents: 4, data: [] },
        indices:    { numComponents: 3, data: [] }
    };

    let vertexIndex = 0;

    // Helper function to add a circle
    function addCircle(centerX, centerY, radius, segments, r, g, b, a) {
        let centerIndex = vertexIndex++;
        
        // Add center vertex
        arrays.a_position.data.push(centerX, centerY);
        arrays.a_color.data.push(r, g, b, a);

        // Add perimeter vertices and create triangles
        for (let i = 0; i <= segments; i++) {
            let angle = (i / segments) * 2 * Math.PI;
            let x = centerX + radius * Math.cos(angle);
            let y = centerY + radius * Math.sin(angle);
            
            arrays.a_position.data.push(x, y);
            arrays.a_color.data.push(r, g, b, a);
            
            if (i > 0) {
                arrays.indices.data.push(centerIndex, vertexIndex - 1, vertexIndex);
            }
            vertexIndex++;
        }
    }

    // Draw a small red circle for the pivot
    addCircle(0, 0, 10.0, 32, 1.0, 0.0, 0.0, 1.0);

    return arrays;
}



main()
